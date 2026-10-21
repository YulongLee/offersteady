"""Synthetic 20 MiB boundary check in disposable, network-isolated local Nginx.

No production URL, credentials, parser, database or document registration is used.
An optional pinned runtime default.conf can be validated without displaying it.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import subprocess
import tempfile
import uuid
from pathlib import Path

from patch_cn_upload_proxy_20m import patch_config


SYNTHETIC_BASELINE = b'''server {
  listen 18080;
  server_name _;
  location /api/ {
    proxy_pass http://127.0.0.1:18081;
    proxy_http_version 1.1;
    proxy_set_header Host $host;
    proxy_set_header X-Request-Id $request_id;
    proxy_set_header Upgrade $http_upgrade;
    proxy_set_header Connection "upgrade";
    proxy_buffering off;
  }
}
'''
MIB = 1024 * 1024
BOUNDARY = "offersteady-synthetic-boundary-20261021"


def docker(args: list[str], *, data: bytes | None = None, timeout: int = 30) -> subprocess.CompletedProcess[bytes]:
    return subprocess.run(["docker", *args], input=data, capture_output=True, timeout=timeout)


def multipart(size: int) -> bytes:
    prefix = (
        f"--{BOUNDARY}\r\n"
        'Content-Disposition: form-data; name="file"; filename="synthetic.pdf"\r\n'
        "Content-Type: application/pdf\r\n\r\n"
    ).encode()
    return prefix + b"S" * size + f"\r\n--{BOUNDARY}--\r\n".encode()


def wrapped(config: bytes) -> bytes:
    return b'''worker_processes 1;
pid /var/run/nginx.pid;
error_log /dev/stderr warn;
events { worker_connections 32; }
http {
  include /etc/nginx/mime.types;
  access_log off;
  client_body_temp_path /var/cache/nginx/client_temp;
''' + config + b'''
  server {
    listen 127.0.0.1:8000;
    listen 127.0.0.1:18081;
    location / {
      client_max_body_size 24m;
      default_type application/json;
      return 202 '{"synthetic":true}';
    }
  }
}
'''


def probe(name: str, *, path: str, file_size: int, listen_port: int, expected: int) -> dict[str, object]:
    if not re.fullmatch(r"/api/v1/[A-Za-z0-9/_-]+", path):
        raise RuntimeError("invalid_synthetic_route")
    body = multipart(file_size)
    # Static synthetic data goes to a tmpfs inside our disposable container.
    # Wget performs the actual HTTP exchange; the upstream only returns 202.
    shell = (
        "cat > /tmp/upload-probe-body; "
        f"wget -S -O - --post-file=/tmp/upload-probe-body --header='Content-Type: multipart/form-data; boundary={BOUNDARY}' "
        f"http://127.0.0.1:{listen_port}{path}; "
        'status=$?; rm -f /tmp/upload-probe-body; exit "$status"'
    )
    process = docker(["exec", "-i", name, "sh", "-c", shell], data=body, timeout=35)
    matches = re.findall(rb"HTTP/1\.[01]\s+(\d{3})", process.stderr)
    status = int(matches[-1]) if matches else 0
    upstream_ok = process.stdout.strip() == b'{"synthetic":true}' if expected == 202 else True
    passed = status == expected and upstream_ok
    return {"route": path, "fileBytes": file_size, "requestBodyBytes": len(body), "status": status, "expectedStatus": expected, "syntheticUpstreamConfirmed": upstream_ok if expected == 202 else None, "passed": passed}


def check_config(image: str, config: bytes, *, listen_port: int, cases: list[tuple[str, int, int]]) -> list[dict[str, object]]:
    name = "offersteady-local-upload-probe-" + uuid.uuid4().hex[:12]
    with tempfile.TemporaryDirectory(prefix="offersteady-upload-nginx-") as folder:
        config_path = Path(folder) / "nginx.conf"
        config_path.write_bytes(wrapped(config))
        options = ["--network", "none", "--read-only", "--memory", "256m", "--pids-limit", "64", "--cpus", "1", "--add-host", "backend:127.0.0.1", "--tmpfs", "/var/cache/nginx:rw,size=64m", "--tmpfs", "/var/run:rw,size=8m", "--tmpfs", "/tmp:rw,size=32m", "--mount", f"type=bind,src={config_path},dst=/etc/nginx/nginx.conf,readonly", "--entrypoint", "nginx"]
        syntax = docker(["run", "--rm", *options, image, "-t"])
        if syntax.returncode:
            raise RuntimeError("isolated_nginx_syntax_failed")
        started = docker(["run", "-d", "--name", name, *options, image, "-g", "daemon off;"])
        if started.returncode:
            raise RuntimeError("isolated_nginx_start_failed")
        try:
            # Running nginx -t after startup also confirms the isolated
            # container is ready without a fixed sleep or production request.
            if docker(["exec", name, "nginx", "-t"]).returncode:
                raise RuntimeError("isolated_nginx_not_ready")
            return [probe(name, path=path, file_size=size, listen_port=listen_port, expected=expected) for path, size, expected in cases]
        finally:
            removed = docker(["rm", "-f", name])
            if removed.returncode:
                raise RuntimeError("isolated_nginx_cleanup_failed")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--image", default="nginx:1.27-alpine")
    parser.add_argument("--baseline-config", type=Path)
    parser.add_argument("--expected-sha256")
    parser.add_argument("--listen-port", type=int)
    args = parser.parse_args()
    try:
        baseline = args.baseline_config.read_bytes() if args.baseline_config else SYNTHETIC_BASELINE
        expected = args.expected_sha256 if args.baseline_config else hashlib.sha256(baseline).hexdigest()
        if not expected:
            raise RuntimeError("pinned_baseline_sha_required")
        port = args.listen_port if args.listen_port else 80 if args.baseline_config else 18080
        if not 1 <= port <= 65535:
            raise RuntimeError("invalid_isolated_listen_port")
        candidate = patch_config(baseline, expected_sha256=expected)
        resolved = docker(["image", "inspect", "--format", "{{.Id}}", args.image])
        image = resolved.stdout.decode().strip()
        if resolved.returncode or not re.fullmatch(r"sha256:[0-9a-f]{64}", image):
            raise RuntimeError("local_image_not_available")
        before = check_config(image, baseline, listen_port=port, cases=[("/api/v1/resume/uploads/proxy", 1536 * 1024, 413)])
        cases = [
            ("/api/v1/resume/uploads/proxy", 20 * MIB, 202),
            ("/api/v1/job-descriptions/uploads/proxy", 20 * MIB, 202),
            ("/api/v1/knowledge/collections/synthetic-collection/uploads/proxy", 20 * MIB, 202),
            ("/api/v1/resume/uploads/proxy", 21 * MIB, 413),
            ("/api/v1/web/state", 1536 * 1024, 413),
            ("/api/v1/resume/uploads/proxy/extra", 1536 * 1024, 413),
        ]
        after = check_config(image, candidate.content, listen_port=port, cases=cases)
        passed = all(item["passed"] for item in [*before, *after])
        print(json.dumps({"ok": passed, "image": image, "network": "none", "productionRequests": 0, "productionDataChanged": False, "baselineSha256": candidate.original_sha256, "candidateSha256": candidate.candidate_sha256, "baseline": before, "candidate": after, "backendFileBoundaryVerifiedSeparately": "test_cn_upload_proxy_overlay.py::test_backend_keeps_exact_20_mib_file_limit"}))
        return 0 if passed else 1
    except Exception as exc:
        # Never print potentially private input config, Docker output or paths.
        allowed = {"invalid_synthetic_route", "isolated_nginx_syntax_failed", "isolated_nginx_start_failed", "isolated_nginx_not_ready", "isolated_nginx_cleanup_failed", "pinned_baseline_sha_required", "invalid_isolated_listen_port", "local_image_not_available", "baseline_sha_mismatch"}
        print(json.dumps({"ok": False, "error": str(exc) if str(exc) in allowed else "isolated_check_failed", "productionRequests": 0}))
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
