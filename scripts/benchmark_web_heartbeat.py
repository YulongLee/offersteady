"""Local-only synthetic PostgreSQL comparison; never use a production DSN."""
from __future__ import annotations

import ast
from concurrent.futures import ThreadPoolExecutor
from dataclasses import replace
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import threading
from time import perf_counter, time
from types import SimpleNamespace

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "apps/backend"))
import psycopg
from psycopg.conninfo import conninfo_to_dict
from psycopg.rows import dict_row
from app.core.config import Settings
from app.core.errors import DomainRequestError
from app.ports.interview_session import SessionBoundDocument
from app.ports.realtime_speech import WebSessionHeartbeatRecord
from app.services.postgres_interview_session_repository import PostgresInterviewSessionRepository
from app.services.realtime_speech_repository import InMemoryRealtimeSpeechRepository
from app.services.realtime_speech_service import RealtimeSpeechService, _now_ms
from app.services.session_service import SessionService

LEGACY_HASH = "0473f0b478cd5a4bdfedf35b41b16f789602e0f66befdbce806935db582f5532"


def legacy_heartbeat():
    source = subprocess.check_output(["git", "show", "HEAD:apps/backend/app/services/realtime_speech_service.py"], cwd=ROOT).decode()
    node = next(n for n in ast.walk(ast.parse(source)) if isinstance(n, ast.FunctionDef) and n.name == "record_web_session_heartbeat")
    assert hashlib.sha256(ast.dump(node, include_attributes=False).encode()).hexdigest() == LEGACY_HASH
    namespace = {"_now_ms": _now_ms, "WebSessionHeartbeatRecord": WebSessionHeartbeatRecord, "DomainRequestError": DomainRequestError}
    exec(compile(ast.Module(body=[node], type_ignores=[]), "verified-legacy-heartbeat", "exec"), namespace)
    return namespace[node.name]


def main():
    dsn = os.environ["OFFERSTEADY_TEST_DATABASE_URL"]
    info = conninfo_to_dict(dsn)
    assert info.get("host") in {"127.0.0.1", "localhost"} and info.get("dbname") == "synthetic_heartbeat"
    settings = Settings(_env_file=None, database_url=dsn, interview_idle_warning_seconds=43200, interview_idle_timeout_seconds=86400)
    sessions_repository = PostgresInterviewSessionRepository(settings)
    counts = {"sessionReads": 0, "materialReads": 0}
    lock = threading.Lock()

    def count(kind):
        with lock:
            counts[kind] += 1

    class CountedSessions:
        def get_session(self, sid):
            count("sessionReads")
            return sessions_repository.get_session(sid)

        def get_heartbeat_state(self, sid):
            count("sessionReads")
            return sessions_repository.get_heartbeat_state(sid)

        def save_session(self, record):
            return sessions_repository.save_session(record)

    class Documents:
        def get_by_id(self, identifier):
            count("materialReads")
            with psycopg.connect(dsn, row_factory=dict_row) as connection:
                row = connection.execute("SELECT * FROM synthetic_heartbeat_bench_docs WHERE document_id=%s", (identifier,)).fetchone()
            return SimpleNamespace(**row) if row else None

    with psycopg.connect(dsn) as connection:
        connection.execute("""CREATE TABLE synthetic_heartbeat_bench_docs (
            document_id text PRIMARY KEY, display_name text, status text, index_state text,
            document_version_id text, summary text, knowledge_collection_id text)""")
        for i in range(3):
            connection.execute("INSERT INTO synthetic_heartbeat_bench_docs VALUES (%s,%s,'ready','indexed','synthetic-version',%s,'synthetic-collection')",
                               (f"synthetic-bench-doc-{i}", f"Synthetic document {i}", "合成资料摘要。" * 256))
    sessions = SessionService(settings=settings, repository=CountedSessions(), document_repository=Documents())
    records = []
    for i in range(10):
        record = sessions.create_session(user_id=f"synthetic-bench-owner-{i}", title="Synthetic heartbeat benchmark")
        bound = [SessionBoundDocument(document_id=f"synthetic-bench-doc-{j}", document_kind="knowledge",
                 display_name=f"Synthetic document {j}", status="ready", index_state="indexed",
                 document_version_id="synthetic-version", summary="合成资料摘要。" * 256,
                 knowledge_collection_id="synthetic-collection") for j in range(3)]
        record = replace(record, status="live", started_at_ms=int(time()*1000),
                         material_binding=replace(record.material_binding, bound_documents=bound))
        sessions_repository.save_session(record)
        records.append(record)
    old = legacy_heartbeat()
    reports = []
    for concurrency in (1, 5, 10):
        for name, operation in [("before", old), ("after", RealtimeSpeechService.record_web_session_heartbeat)]:
            service = object.__new__(RealtimeSpeechService)
            service.settings, service.session_service = settings, sessions
            service.repository = InMemoryRealtimeSpeechRepository()
            service._session_activity_lock = threading.Lock()
            service._session_last_activity_ms, service._session_owners = {}, {}
            with lock:
                counts.update(sessionReads=0, materialReads=0)
            def run(index):
                record = records[index % concurrency]
                start = perf_counter()
                operation(service, user_id=record.owner_user_id, session_id=record.session_id, binding_id=None, page="live")
                return (perf_counter()-start)*1000
            with ThreadPoolExecutor(max_workers=concurrency) as pool:
                durations = sorted(pool.map(run, range(60)))
            def percentile(p): return round(durations[min(len(durations)-1, int((len(durations)-1)*p))], 3)
            reports.append({"version":name,"concurrency":concurrency,"samples":len(durations),"failures":0,
                "p50Ms":percentile(.50),"p95Ms":percentile(.95),"p99Ms":percentile(.99),**counts})
    print(json.dumps({"syntheticLocalOnly":True,"materialsPerSession":3,"reports":reports,"notProductionApiP95":True}))


if __name__ == "__main__":
    main()
