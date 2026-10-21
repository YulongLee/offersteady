"""Read-only conservative TCP 8000 connection aggregate inside the Backend.

Established idle keepalives also defer release. This is not perfect in-flight
request detection and never reads, logs or returns addresses or request data.
"""
from pathlib import Path
import hashlib
import json
import re
import time


class TCPTableError(ValueError):
    pass


def count_established(table: str, *, ipv6: bool) -> tuple[int, int]:
    if not isinstance(table, str):
        raise TCPTableError()
    lines = table.splitlines()
    if not lines or len(lines) > 100_001:
        raise TCPTableError()
    header = lines[0].split()
    if len(header) < 4 or header[:2] != ["sl", "local_address"] or header[2] not in {"rem_address", "remote_address"} or header[3] != "st":
        raise TCPTableError()
    width = 32 if ipv6 else 8
    address = re.compile(r"[0-9A-Fa-f]{" + str(width) + r"}:[0-9A-Fa-f]{4}")
    count = rows = 0
    for line in lines[1:]:
        if not line.strip():
            continue
        parts = line.split()
        if (len(parts) < 10 or not re.fullmatch(r"\d+:", parts[0])
                or not address.fullmatch(parts[1]) or not address.fullmatch(parts[2])
                or not re.fullmatch(r"[0-9A-Fa-f]{2}", parts[3])
                or not 1 <= int(parts[3], 16) <= 12):
            raise TCPTableError()
        rows += 1
        if int(parts[1].rsplit(":", 1)[1], 16) == 8000 and int(parts[3], 16) == 1:
            count += 1
    return count, rows


def network_namespace() -> str:
    current = str(Path('/proc/self/ns/net').readlink())
    init = str(Path('/proc/1/ns/net').readlink())
    if current != init or not re.fullmatch(r'net:\[[1-9][0-9]*\]', current):
        raise TCPTableError()
    return hashlib.sha256(current.encode('ascii')).hexdigest()


def main():
    namespace = network_namespace()
    count = rows = 0
    for path, ipv6 in (("/proc/net/tcp", False), ("/proc/net/tcp6", True)):
        found, scanned = count_established(Path(path).read_text(encoding="ascii"), ipv6=ipv6)
        count += found
        rows += scanned
    if network_namespace() != namespace:
        raise TCPTableError()
    return {"passed": True, "atMs": int(time.time() * 1000), "establishedPort8000": count,
            "tablesRead": 2, "scannedRows": rows, "scope": "container_tcp8000_established_only",
            "networkNamespaceSha256": namespace}


if __name__ == "__main__":
    try:
        print(json.dumps(main()))
    except Exception:
        print(json.dumps({"passed": False, "reason": "tcp_read_or_parse_failed"}))
        raise SystemExit(2) from None
