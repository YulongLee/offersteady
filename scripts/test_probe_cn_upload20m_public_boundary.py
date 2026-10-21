"""Synthetic loopback regression only; never uses public services or user data."""
import importlib.util
import json
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
import socket
import subprocess
import sys
import threading
import unittest
from unittest.mock import patch


SOURCE = Path(__file__).with_name('probe_cn_upload20m_public_boundary.py')
SPEC = importlib.util.spec_from_file_location('upload_boundary_probe_under_test', SOURCE)
PROBE = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = PROBE
SPEC.loader.exec_module(PROBE)


class EarlyResponseHandler(BaseHTTPRequestHandler):
    protocol_version = 'HTTP/1.1'

    def handle_expect_100(self):
        self.server.observed.append((self.path, self.headers.get('Expect'),
                                     int(self.headers['Content-Length'])))
        if self.server.drop_connection:
            self.close_connection = True
            self.connection.shutdown(socket.SHUT_RDWR)
            self.connection.close()
            return False
        status = 401 if self.path == PROBE.ROUTES[0][0] else 413
        self.send_response(status)
        self.send_header('Content-Length', '0')
        self.send_header('Connection', 'close')
        self.end_headers()
        self.close_connection = True
        return False

    def do_POST(self):
        self.server.body_handlers_called += 1
        self.send_error(500)

    def log_message(self, *args):
        pass


class PublicBoundaryProbeTests(unittest.TestCase):
    def setUp(self):
        self.server = ThreadingHTTPServer(('127.0.0.1', 0), EarlyResponseHandler)
        self.server.observed = []
        self.server.body_handlers_called = 0
        self.server.drop_connection = False
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()
        self.origin = f'http://127.0.0.1:{self.server.server_port}'

    def tearDown(self):
        self.server.shutdown()
        self.server.server_close()
        self.thread.join(2)

    def test_early_401_and_413_are_received_without_sending_body(self):
        result = PROBE.run_probe(self.origin)
        self.assertTrue(result['passed'])
        self.assertEqual([(r['status'], r['curlReturnCode']) for r in result['records']],
                         [(401, 0), (413, 0)])
        self.assertEqual(result['requestCount'], 2)
        self.assertEqual(self.server.body_handlers_called, 0)
        self.assertEqual(len(self.server.observed), 2)
        self.assertTrue(all(expect == '100-continue' and size > PROBE.FILE_BYTES
                            for _, expect, size in self.server.observed))
        self.assertEqual(result['documentWrites'], 0)
        self.assertEqual(result['modelCalls'], 0)

    def test_connection_closed_without_response_cannot_pass(self):
        self.server.drop_connection = True
        result = PROBE.run_probe(self.origin)
        self.assertFalse(result['passed'])
        self.assertEqual(result['requestCount'], 2)
        self.assertTrue(all(r['status'] is None and r['curlReturnCode'] != 0
                            for r in result['records']))

    def test_http_status_alone_cannot_hide_transport_failure(self):
        failed = subprocess.CompletedProcess([], 56, stdout='413', stderr='private synthetic diagnostic')
        with patch.object(PROBE.subprocess, 'run', return_value=failed) as run:
            result = PROBE.run_probe(self.origin)
        self.assertFalse(result['passed'])
        self.assertTrue(all(r['curlReturnCode'] == 56 for r in result['records']))
        self.assertNotIn('private synthetic diagnostic', json.dumps(result))
        command = run.call_args.args[0]
        self.assertEqual(command[:2], ['curl', '--disable'])
        self.assertNotIn('--insecure', command)
        self.assertNotIn('-k', command)
        self.assertNotIn('--location', command)
        self.assertNotIn('--retry', command)

    def test_timeout_is_bounded_and_cannot_pass(self):
        with patch.object(PROBE.subprocess, 'run', side_effect=subprocess.TimeoutExpired('curl', 23)):
            result = PROBE.run_probe(self.origin)
        self.assertFalse(result['passed'])
        self.assertTrue(all(r['status'] is None and r['curlReturnCode'] == -1
                            for r in result['records']))


if __name__ == '__main__':
    unittest.main()
