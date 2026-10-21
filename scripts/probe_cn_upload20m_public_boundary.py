"""Two bounded anonymous rejection-path checks, never valid material uploads.

Expect: 100-continue lets an early 401/413 complete before the synthetic body
is sent. A received status is accepted only when curl also reports transport
success. TLS verification stays enabled; response bodies and stderr are never
included in the aggregate receipt. Importing this module makes no requests.
"""
from __future__ import annotations

import json
import os
from pathlib import Path
import re
import subprocess
import tempfile


PUBLIC_ORIGIN = 'https://mianshiwen.cn'
BOUNDARY = 'offersteady-no-auth-synthetic-boundary-20261021'
FILE_BYTES = 1536 * 1024
ROUTES = (
    ('/api/v1/resume/uploads/proxy', frozenset({401, 422})),
    ('/api/v1/web/state', frozenset({413})),
)


def write_synthetic_body(path: Path) -> None:
    prefix = (f'--{BOUNDARY}\r\nContent-Disposition: form-data; name="file"; '
              'filename="synthetic.pdf"\r\nContent-Type: application/pdf\r\n\r\n').encode()
    # Missing userId, intentId, objectKey and contentType prevent registration,
    # even if an authentication policy were to change. No valid PDF is used.
    with path.open('wb') as stream:
        stream.write(prefix)
        stream.write(b'S' * FILE_BYTES)
        stream.write(f'\r\n--{BOUNDARY}--\r\n'.encode())


def rejection_status(url: str, body_path: Path) -> tuple[int | None, int]:
    command = [
        'curl', '--disable', '--silent', '--show-error', '--http1.1',
        '--max-time', '20', '--output', os.devnull,
        '--write-out', '%{http_code}', '--request', 'POST',
        '--header', f'Content-Type: multipart/form-data; boundary={BOUNDARY}',
        '--header', 'Cache-Control: no-cache',
        '--header', 'Expect: 100-continue',
        '--data-binary', '@' + str(body_path), '--url', url,
    ]
    try:
        response = subprocess.run(command, capture_output=True, text=True, timeout=23)
    except subprocess.TimeoutExpired:
        return None, -1
    except OSError:
        return None, -2
    raw_status = response.stdout.strip()
    status = int(raw_status) if re.fullmatch(r'[1-5][0-9]{2}', raw_status) else None
    return status, response.returncode


def run_probe(origin: str = PUBLIC_ORIGIN) -> dict:
    records = []
    with tempfile.TemporaryDirectory(prefix='offersteady-anonymous-upload-probe-') as directory:
        body_path = Path(directory) / 'synthetic-multipart.bin'
        write_synthetic_body(body_path)
        for path, expected in ROUTES:
            status, returncode = rejection_status(origin + path, body_path)
            records.append({
                'route': path, 'status': status, 'curlReturnCode': returncode,
                'passed': returncode == 0 and status in expected,
                'fileBytes': FILE_BYTES, 'authenticated': False,
            })
    return {
        'passed': all(record['passed'] for record in records), 'records': records,
        'requestCount': len(records), 'documentWrites': 0, 'modelCalls': 0,
        'userRecordsUsed': False,
    }


def main() -> None:
    result = run_probe()
    print(json.dumps(result))
    raise SystemExit(0 if result['passed'] else 1)


if __name__ == '__main__':
    main()
