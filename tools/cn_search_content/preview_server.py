"""Loopback-only preview of the CN static candidate; never forwards requests.

The anonymous fixture contains synthetic empty user state and explicitly sourced
public metadata. These API responses exist only in this local review server.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
import mimetypes
from pathlib import Path
import re
from urllib.parse import unquote, urlsplit


REPO = Path(__file__).resolve().parents[2]
DEFAULT_ROOT = REPO / 'artifacts/cn-search-content-20261026/candidate/html'
SEALED_NGINX = REPO / 'releases/cn-20261022.1/nginx/default.conf'
FIXTURE = Path(__file__).with_name('anonymous-fixture.json')
APP_ROUTE = re.compile(
    r'^/(?:login|error|invite/[^/]+|app(?:/written-exams(?:/new)?'
    r'|/mock-interviews(?:/[^/]+)?|/interviews/new'
    r'|/interviews/[^/]+/(?:prepare|live|review)|/library|/resume-optimizer'
    r'|/billing|/partner-program|/guide|/devices|/settings)?)/?$'
)
PUBLIC_LEAVES = {'pricing', 'download', 'security', 'about', 'contact'}
PUBLIC_HUBS = {'features', 'guides', 'interview-questions'}
FEATURES = {'ai-interview-assistant', 'realtime-interview', 'screenshot-answer', 'interview-review'}
GUIDES = {
    'audio-troubleshooting', 'interview-preparation', 'macos-permissions',
    'feishu-audio-setup', 'tencent-meeting-audio-setup', 'star-interview-answer',
    'self-introduction', 'project-experience', 'technical-interview', 'common-interview-questions',
}
TOPICS = {'llm', 'rag', 'ai-agent', 'java-backend', 'frontend', 'algorithms'}


def envelope(data=None, *, code=None, message=None):
    return {
        'success': code is None, 'data': data,
        'error': None if code is None else {'code': code, 'message': message},
        'requestId': 'local-preview-synthetic',
        'meta': {'apiVersion': 'v1', 'timestamp': datetime.now(timezone.utc).isoformat()},
    }


def mapped_file(path: str) -> str | None:
    """Mirror sealed public/SPA routes, without its API and promotion proxies."""
    if path == '/':
        return 'index.html'
    if path.rstrip('/') == '/guide':
        return 'guide.html'
    clean = path.strip('/')
    if clean in PUBLIC_LEAVES | PUBLIC_HUBS:
        return f'seo/{clean}.html'
    parts = clean.split('/')
    if len(parts) == 2:
        family, leaf = parts
        if (family == 'features' and leaf in FEATURES
                or family == 'guides' and leaf in GUIDES
                or family == 'interview-questions' and leaf in TOPICS):
            return f'seo/{leaf}.html'
    if clean in {'terms', 'privacy'}:
        return f'{clean}.html'
    if APP_ROUTE.fullmatch(path):
        return 'index.html'
    if path in {'/robots.txt', '/sitemap.xml', '/llms.txt', '/llms-full.txt', '/public-facts.json', '/offersteady-build.json'}:
        return path[1:]
    if path.startswith(('/assets/', '/media/')) or path == '/seo/public-search.css':
        return path[1:]
    return None


def preview_badge(path: str, catalog_date: str = '2026-10-10') -> bytes:
    prices = f' · 价格快照 {catalog_date}' if path.rstrip('/') in {'', '/pricing'} else ''
    return (
        '<aside data-local-preview="synthetic" aria-label="本地预览状态" '
        'style="position:fixed;bottom:10px;left:10px;z-index:2147483647;'
        'padding:6px 10px;border:1px solid #38534e;border-radius:8px;'
        'background:#10241feb;color:#c8e5d9;font:12px/1.5 sans-serif;'
        'max-width:calc(100vw - 40px);pointer-events:none">'
        f'本地预览 · 未上线{prices}</aside>'
    ).encode()


def make_handler(root: Path, fixture: dict, csp: str):
    catalog_date = fixture['_preview']['catalogSnapshotAt'][:10]
    if not re.fullmatch(r'\d{4}-\d{2}-\d{2}', catalog_date):
        raise ValueError('invalid fixture catalog date')
    class PreviewHandler(BaseHTTPRequestHandler):
        server_version = 'OfferSteadyLocalPreview/1'

        def log_message(self, _format, *_args):
            # Paths, headers and request bodies may contain user-entered data.
            pass

        def headers_for(self, status, kind, length, **extra):
            self.send_response(status)
            self.send_header('Content-Type', kind)
            self.send_header('Content-Length', str(length))
            self.send_header('Cache-Control', 'no-store')
            self.send_header('X-Robots-Tag', 'noindex, nofollow')
            self.send_header('X-Offersteady-Preview', 'synthetic; local-only; no-forwarding')
            self.send_header('Content-Security-Policy', csp)
            self.send_header('X-Content-Type-Options', 'nosniff')
            self.send_header('X-Frame-Options', 'DENY')
            self.send_header('Referrer-Policy', 'no-referrer')
            for name, value in extra.items():
                self.send_header(name.replace('_', '-'), value)
            self.end_headers()

        def send_bytes(self, status, data, kind='application/json; charset=utf-8', **extra):
            self.headers_for(status, kind, len(data), **extra)
            if self.command != 'HEAD':
                try:
                    self.wfile.write(data)
                except (BrokenPipeError, ConnectionResetError):
                    pass

        def json(self, status, value, **extra):
            self.send_bytes(status, json.dumps(value, ensure_ascii=False).encode(), **extra)

        def do_GET(self):
            try:
                path = unquote(urlsplit(self.path).path, errors='strict')
            except (UnicodeError, ValueError):
                self.json(400, envelope(code='invalid_path', message='本地预览地址无效'))
                return
            if '\\' in path or '\x00' in path or '..' in path.split('/'):
                self.json(400, envelope(code='invalid_path', message='本地预览地址无效'))
                return
            if path.startswith('/api/'):
                routes = {
                    '/api/v1/web/state': 'state',
                    '/api/v1/system/foundation': 'foundation',
                    '/api/v1/partner-program/config': 'partnerProgramConfig',
                }
                key = routes.get(path)
                if key:
                    self.json(200, envelope(fixture[key]))
                else:
                    self.json(401 if '/auth/' in path else 404,
                              envelope(code='local_preview_only', message='本地仅预览公开页面，不提供登录或业务服务'))
                return
            if path == '/robots.txt':
                self.send_bytes(200, b'User-agent: *\nDisallow: /\n', 'text/plain; charset=utf-8')
                return
            relative = mapped_file(path)
            target = (root / relative).resolve() if relative else root / '__missing__'
            if not target.is_relative_to(root) or not target.is_file():
                fallback = root / '404.html'
                data = fallback.read_bytes() if fallback.is_file() else b'<!doctype html><title>Not found</title><h1>404</h1>'
                self.send_bytes(404, data.replace(b'</body>', preview_badge(path, catalog_date)+b'</body>'), 'text/html; charset=utf-8')
                return
            kind = mimetypes.guess_type(target.name)[0] or 'application/octet-stream'
            if target.suffix == '.js':
                kind = 'text/javascript'
            if kind == 'text/html':
                data = target.read_bytes()
                if data.count(b'</body>') == 1:
                    data = data.replace(b'</body>', preview_badge(path, catalog_date)+b'</body>')
                self.send_bytes(200, data, kind+'; charset=utf-8')
                return
            size = target.stat().st_size
            start, end, status = 0, size-1, HTTPStatus.OK
            extra = {'Accept_Ranges': 'bytes'}
            requested = self.headers.get('Range')
            if requested:
                match = re.fullmatch(r'bytes=(\d*)-(\d*)', requested.strip())
                if not match or not any(match.groups()) or size == 0:
                    self.send_bytes(416, b'', Content_Range=f'bytes */{size}')
                    return
                left, right = match.groups()
                if left:
                    start = int(left)
                    end = min(int(right), size-1) if right else size-1
                else:
                    start = max(0, size-int(right))
                if start > end or start >= size:
                    self.send_bytes(416, b'', Content_Range=f'bytes */{size}')
                    return
                status = HTTPStatus.PARTIAL_CONTENT
                extra['Content_Range'] = f'bytes {start}-{end}/{size}'
            self.headers_for(status, kind, max(0, end-start+1), **extra)
            if self.command == 'HEAD':
                return
            try:
                with target.open('rb') as handle:
                    handle.seek(start)
                    remaining = end-start+1
                    while remaining > 0:
                        chunk = handle.read(min(remaining, 64*1024))
                        if not chunk:
                            break
                        self.wfile.write(chunk)
                        remaining -= len(chunk)
            except (BrokenPipeError, ConnectionResetError):
                pass

        do_HEAD = do_GET

        def reject_mutation(self):
            self.json(405, envelope(code='local_preview_read_only', message='本地预览不执行登录、付费、上传或业务操作'), Allow='GET, HEAD')

        do_POST = reject_mutation
        do_PUT = reject_mutation
        do_PATCH = reject_mutation
        do_DELETE = reject_mutation
        do_OPTIONS = reject_mutation
        do_TRACE = reject_mutation
        do_CONNECT = reject_mutation

    return PreviewHandler


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', type=Path, default=DEFAULT_ROOT)
    parser.add_argument('--port', type=int, default=5183)
    parser.add_argument('--nginx', type=Path, default=SEALED_NGINX)
    args = parser.parse_args()
    root = args.root.resolve()
    if not (root/'index.html').is_file():
        parser.error('candidate index.html missing; run build_preview.py first')
    match = re.search(r'set \$offersteady_csp "([^"]+)";', args.nginx.read_text())
    if not match:
        parser.error('sealed Content-Security-Policy missing')
    fixture = json.loads(FIXTURE.read_text())
    if fixture.get('_preview', {}).get('containsUserData') is not False:
        parser.error('fixture must be explicitly anonymous')
    with ThreadingHTTPServer(('127.0.0.1', args.port), make_handler(root, fixture, match.group(1))) as server:
        print(f'Local-only preview: http://127.0.0.1:{args.port}/ (writes blocked; no forwarding)', flush=True)
        try:
            server.serve_forever()
        except KeyboardInterrupt:
            pass


if __name__ == '__main__':
    main()
