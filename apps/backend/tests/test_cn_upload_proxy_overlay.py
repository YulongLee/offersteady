from __future__ import annotations

import hashlib
import importlib.util
import subprocess
import sys
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[3]
TOOL_PATH = ROOT / "scripts/patch_cn_upload_proxy_20m.py"
spec = importlib.util.spec_from_file_location("cn_upload_proxy_overlay", TOOL_PATH)
assert spec and spec.loader
tool = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = tool
spec.loader.exec_module(tool)

# Synthetic missing-limit fixture mirrors the production failure shape, not
# actual production configuration, identifiers, URLs or user records.
BASELINE = b'''server {
  listen 8080;
  set $csp "script-src 'self' 'sha256-synthetic'; connect-src https:;";
  add_header Content-Security-Policy $csp always;
  location ~ ^/api/v1/realtime-speech/sessions/[^/]+/stream$ {
    proxy_pass http://127.0.0.1:18081;
    proxy_buffering off;
  }
  location /api/ {
    proxy_pass http://127.0.0.1:18081;
    proxy_http_version 1.1;
    proxy_set_header Host $host;
    proxy_set_header X-Request-Id $request_id;
    proxy_set_header Upgrade $http_upgrade;
    proxy_set_header Connection "upgrade";
    proxy_read_timeout 3600s;
    proxy_send_timeout 3600s;
    proxy_buffering off;
  }
  location ~* "^/assets/[A-Za-z0-9_-]{8}\\.js$" { try_files $uri =404; }
  location = /app/mock-interviews { return 200 'synthetic mock route'; }
  location = /app/resume-optimizer { return 200 'synthetic resume route'; }
}
'''


def patch(source: bytes = BASELINE):
    return tool.patch_config(source, expected_sha256=hashlib.sha256(source).hexdigest())


def test_reproduces_missing_proxy_limit_and_only_inserts_one_scoped_block():
    assert b"client_max_body_size" not in BASELINE
    result = patch()
    text = result.content.decode()
    assert text.count("client_max_body_size 21m;") == 1
    inserted = result.content[len(BASELINE.split(b"  location /api/ {")[0]):]
    assert inserted.startswith(b"  # CN material upload envelope")
    start = result.content.index(tool.PATCH_MARKER.encode()) - 2
    end = result.content.index(b"  location /api/ {")
    assert result.content[:start] + result.content[end:] == BASELINE
    assert result.inserted_bytes == end - start
    assert result.original_sha256 == hashlib.sha256(BASELINE).hexdigest()
    assert result.candidate_sha256 == hashlib.sha256(result.content).hexdigest()


def test_added_block_preserves_actual_upstream_and_request_headers_without_websocket_upgrade():
    text = patch().content.decode()
    scoped = text.split(tool.UPLOAD_LOCATION + " {", 1)[1].split("\n  }", 1)[0]
    assert "proxy_pass http://127.0.0.1:18081;" in scoped
    assert "proxy_set_header X-Request-Id $request_id;" in scoped
    assert "proxy_http_version 1.1;" in scoped
    assert "proxy_read_timeout 3600s;" in scoped
    assert "proxy_set_header Upgrade" not in scoped
    assert "proxy_set_header Connection" not in scoped
    generic = text.split("  location /api/ {", 1)[1].split("\n  }", 1)[0]
    assert "client_max_body_size" not in generic
    assert 'proxy_set_header Connection "upgrade";' in generic


@pytest.mark.parametrize("path", tool.SAMPLE_PATHS)
def test_scoped_match_covers_each_supported_material_route(path):
    import re
    assert re.fullmatch(tool.UPLOAD_PATTERN, path)


@pytest.mark.parametrize("path", [
    "/api/v1/web/state", "/api/v1/resume/uploads/complete",
    "/api/v1/resume/uploads/proxy/extra", "/api/v1/resume/uploads/proxy/",
    "/api/v1/resume-optimizer/jobs", "/api/v1/knowledge/collections/a/b/uploads/proxy",
])
def test_scoped_match_excludes_neighboring_and_unrelated_routes(path):
    import re
    assert not re.fullmatch(tool.UPLOAD_PATTERN, path)


def test_refuses_a_stale_or_missing_baseline_hash():
    with pytest.raises(tool.PatchRefused, match="baseline_sha_mismatch"):
        tool.patch_config(BASELINE, expected_sha256="0" * 64)
    with pytest.raises(tool.PatchRefused, match="baseline_sha_mismatch"):
        tool.patch_config(BASELINE, expected_sha256="")


def test_refuses_to_duplicate_an_already_patched_location():
    with pytest.raises(tool.PatchRefused, match="already_patched"):
        patch(patch().content)


@pytest.mark.parametrize(("change", "code"), [
    (lambda b: b.replace(b"location /api/", b"location ^~ /api/"), "expected_single_generic_api_location"),
    (lambda b: b.replace(b"location /api/ {", b"location /api/ {\n    client_max_body_size 2m;"), "unexpected_generic_api_size_limit"),
    (lambda b: b.replace(b"  location /api/ {", b"  location ^~ /api/v1/ { return 404; }\n  location /api/ {"), "shadowing_prefix_location"),
    (lambda b: b.replace(b"  location /api/ {", b"  location ~ ^/api/ { return 404; }\n  location /api/ {"), "shadowing_regex_location"),
    (lambda b: b.replace(b"  location /api/ {", b"  location = /api/v1/resume/uploads/proxy { return 404; }\n  location /api/ {"), "existing_upload_proxy_location"),
    (lambda b: b + b"server { listen 8081; }\n", "expected_single_server"),
    (lambda b: b.replace(b"location /api/ {", b"location /api/ { include extra.conf;"), "unsupported_api_include"),
])
def test_refuses_conflicting_or_unknown_routing_instead_of_silently_changing_it(change, code):
    with pytest.raises(tool.PatchRefused, match=code):
        patch(change(BASELINE))


def test_headers_are_case_insensitive_in_upload_clone():
    source = BASELINE.replace(b"proxy_set_header Upgrade", b"proxy_set_header upgrade").replace(b"proxy_set_header Connection", b"proxy_set_header connection")
    scoped = patch(source).content.decode().split(tool.UPLOAD_LOCATION + " {", 1)[1].split("\n  }", 1)[0]
    assert "proxy_set_header upgrade" not in scoped
    assert "proxy_set_header connection" not in scoped


def test_cli_never_overwrites_its_input_or_existing_output(tmp_path):
    source = tmp_path / "baseline.conf"
    source.write_bytes(BASELINE)
    args = [sys.executable, str(TOOL_PATH), "--input", str(source), "--expected-sha256", hashlib.sha256(BASELINE).hexdigest(), "--output"]
    assert subprocess.run([*args, str(source)], capture_output=True).returncode == 2
    output = tmp_path / "candidate.conf"
    assert subprocess.run([*args, str(output)], capture_output=True).returncode == 0
    first = output.read_bytes()
    assert first == patch().content
    assert subprocess.run([*args, str(output)], capture_output=True).returncode == 2
    assert source.read_bytes() == BASELINE
    assert output.read_bytes() == first


def test_backend_keeps_exact_20_mib_file_limit():
    from app.core.errors import DomainRequestError
    from app.services.document_service import DocumentService
    service = DocumentService(storage=None, repository=None, knowledge_store=None)
    assert service.validation_policy().max_file_size_bytes == 20 * 1024 * 1024
    assert service._validate_file(filename="synthetic.pdf", content_type="application/pdf", size_bytes=20 * 1024 * 1024) == "pdf"
    with pytest.raises(DomainRequestError):
        service._validate_file(filename="synthetic.pdf", content_type="application/pdf", size_bytes=20 * 1024 * 1024 + 1)
