"""Exercise the real telemetry route/service without providers or production data.

Also runnable with unittest inside a --network none production-image container.
"""
from __future__ import annotations

from collections import deque
import logging
import os
from pathlib import Path
import threading
from types import SimpleNamespace
import unittest

from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.core.errors import DomainRequestError, install_exception_handlers
from app.deps import optional_authenticated_context, realtime_speech_service
from app.modules.realtime_speech import router
from app.ports.authentication import AuthenticatedRequestContext
import app.services.realtime_speech_service as service_module
from app.services.realtime_speech_service import RealtimeSpeechService


ENTRY_TIMING = {
    "routeReceivedAtMs": 100,
    "executorAdmittedAtMs": 120,
    "answerGeneratorStartedAtMs": 150,
}
STAGES = ("transcript-delivery", "transcript-render", "answer-first-render", "screenshot-first-render")


class RuntimePerformanceAckCompatibilityTest(unittest.TestCase):
    def setUp(self) -> None:
        expected_root = os.environ.get("OFFERSTEADY_ACK_TEST_SOURCE_ROOT")
        if expected_root:
            self.assertTrue(Path(service_module.__file__).resolve().is_relative_to(Path(expected_root).resolve()))
        self.owner = "synthetic-ack-owner"
        self.session_id = "synthetic-ack-session"
        self.checked_sessions: list[tuple[str, str]] = []
        # Keep the actual acknowledgement, trace storage and summary methods;
        # skip unrelated provider/thread initialization for this isolated test.
        self.service = object.__new__(RealtimeSpeechService)
        self.service.settings = SimpleNamespace(app_name="ack-regression", environment="test")
        self.service.logger = logging.getLogger("ack-regression")
        self.service.logger.addHandler(logging.NullHandler())
        self.service.session_service = SimpleNamespace(get_session=self.get_session)
        self.service._trace_lock = threading.Lock()
        self.service._trace_records = {}
        self.service._trace_order = deque(maxlen=4096)
        self.service._latest_timing = lambda **kwargs: None

        app = FastAPI()
        app.include_router(router, prefix="/api/v1")
        install_exception_handlers(app, settings=self.service.settings, logger=self.service.logger)
        app.dependency_overrides[realtime_speech_service] = lambda: self.service
        app.dependency_overrides[optional_authenticated_context] = lambda: AuthenticatedRequestContext(
            user_id=self.owner, login_id="synthetic-login", auth_session_id="synthetic-auth",
        )
        self.client = TestClient(app, raise_server_exceptions=False)
        self.addCleanup(self.client.close)

    def get_session(self, *, user_id: str, session_id: str):
        self.checked_sessions.append((user_id, session_id))
        if user_id != self.owner or session_id != self.session_id:
            raise DomainRequestError("interview-session", "read", "Synthetic session is not owned", 404)
        return SimpleNamespace(session_id=session_id, user_id=user_id)

    def post(self, *, stage="answer-first-render", fields=None, session_id=None):
        return self.client.post(
            f"/api/v1/realtime-speech/sessions/{session_id or self.session_id}/performance-ack",
            json={"userId": self.owner, "traceId": "synthetic-trace", "stage": stage,
                  "durationMs": 60, **(fields or {})},
        )

    def test_all_stages_accept_populated_entry_timestamps(self):
        for stage in STAGES:
            with self.subTest(stage=stage):
                self.service._trace_records.clear()
                self.service._trace_order.clear()
                response = self.post(stage=stage, fields=ENTRY_TIMING)
                self.assertEqual(response.status_code, 200, response.text)
                self.assertTrue(response.json()["data"]["accepted"])
                trace = self.service._trace_snapshot("synthetic-trace")
                for key, value in ENTRY_TIMING.items():
                    self.assertEqual(trace[key], value)
                self.assertEqual(trace["telemetryStage"], stage)
                self.assertFalse({"question", "answer", "transcript", "content", "prompt"} & trace.keys())
        self.assertEqual(len(self.checked_sessions), len(STAGES))

    def test_all_stages_accept_omitted_or_null_entry_timestamps(self):
        for stage in STAGES:
            for fields in ({}, dict.fromkeys(ENTRY_TIMING)):
                with self.subTest(stage=stage, fields=fields):
                    response = self.post(stage=stage, fields=fields)
                    self.assertEqual(response.status_code, 200, response.text)
                    trace = self.service._trace_snapshot("synthetic-trace")
                    self.assertFalse(ENTRY_TIMING.keys() & trace.keys())

    def test_rejects_non_owned_session_before_recording(self):
        response = self.post(session_id="synthetic-other-session", fields=ENTRY_TIMING)
        self.assertEqual(response.status_code, 404)
        self.assertEqual(self.service._trace_records, {})

    def test_rejects_conflicting_user_identity(self):
        response = self.post(fields={"userId": "synthetic-other-owner"})
        self.assertEqual(response.status_code, 403)
        self.assertEqual(self.checked_sessions, [])
        self.assertEqual(self.service._trace_records, {})

    def test_rejects_private_content_and_invalid_timing(self):
        for fields in ({"content": "synthetic-only"}, {"transcript": "synthetic-only"},
                       {"routeReceivedAtMs": -1}, {"durationMs": 120001}):
            with self.subTest(fields=fields):
                self.assertEqual(self.post(fields=fields).status_code, 422)
        self.assertEqual(self.service._trace_records, {})

    def test_summary_retains_entry_timing_distributions(self):
        self.assertEqual(self.post(fields=ENTRY_TIMING).status_code, 200)
        summary = self.service.performance_summary(session_id=self.session_id)["distributions"]
        for key, value in (("answerRouteToExecutorAdmissionMs", 20),
                           ("answerExecutorAdmissionToGeneratorMs", 30),
                           ("answerRouteToGeneratorMs", 50)):
            self.assertEqual(summary[key]["count"], 1)
            self.assertEqual(summary[key]["p95"], value)


if __name__ == "__main__":
    print(f"Tested service source: {service_module.__file__}", flush=True)
    unittest.main(verbosity=2)
