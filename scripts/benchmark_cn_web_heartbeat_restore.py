"""Compare the verified running CN method with its isolated local restoration.

Uses the existing synthetic PostgreSQL benchmark, restricted to loopback and
the synthetic_heartbeat database. Does not use production credentials or users.
"""
from __future__ import annotations

import argparse
import ast
import hashlib
import importlib.util
from pathlib import Path
import sys


SOURCE_BEFORE_SHA256 = "0f0b280f284b35625fc75d7615c1c2f43bf731f68230928ef6881c1fd86875a7"


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--backend-path", type=Path, required=True)
    parser.add_argument("--baseline-source", type=Path, required=True)
    args = parser.parse_args()
    backend = args.backend_path.resolve()
    sys.path.insert(0, str(backend))
    import app.services.realtime_speech_service as runtime
    assert Path(runtime.__file__).resolve() == backend / "app/services/realtime_speech_service.py", "candidate import drift"

    before = args.baseline_source.read_bytes()
    assert hashlib.sha256(before).hexdigest() == SOURCE_BEFORE_SHA256, "running source baseline drift"
    tree = ast.parse(before)
    cls = next(node for node in tree.body if isinstance(node, ast.ClassDef) and node.name == "RealtimeSpeechService")
    method = next(node for node in cls.body if isinstance(node, ast.FunctionDef) and node.name == "record_web_session_heartbeat")

    path = Path(__file__).with_name("benchmark_web_heartbeat.py")
    spec = importlib.util.spec_from_file_location("synthetic_heartbeat_benchmark", path)
    benchmark = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(benchmark)
    assert benchmark.RealtimeSpeechService is runtime.RealtimeSpeechService, "benchmark candidate drift"
    namespace = {
        "_now_ms": runtime._now_ms,
        "WebSessionHeartbeatRecord": runtime.WebSessionHeartbeatRecord,
        "DomainRequestError": runtime.DomainRequestError,
    }
    exec(compile(ast.Module(body=[method], type_ignores=[]), "verified-running-heartbeat", "exec"), namespace)
    benchmark.legacy_heartbeat = lambda: namespace[method.name]
    benchmark.main()


if __name__ == "__main__":
    main()
