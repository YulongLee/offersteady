"""Isolated local comparison of actual CN auth/session repository operations.

Uses synthetic test setup and test-only timing proxies. No DSN, SQL, parameters,
identifiers or result bodies are emitted. Requires the dev pytest environment
and the separately supplied pinned pool package on PYTHONPATH.
"""
from __future__ import annotations

import argparse
from concurrent.futures import ThreadPoolExecutor
from contextlib import ExitStack
from dataclasses import dataclass, field
import json
import math
import os
from pathlib import Path
from threading import Lock
from time import perf_counter, sleep, monotonic
import sys

import psycopg

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "apps/backend/tests"))
from app.platform import cn_hot_database as provider
from test_cn_hot_database import persistent_repositories
from connection_pool_eval import validate_local_dsn


@dataclass
class Counter:
    lock: object = field(default_factory=Lock)
    timings: dict[str, list[float]] = field(default_factory=lambda: {
        "connect": [], "applicationQuery": [], "healthRoundTrip": [],
    })

    def record(self, name, elapsed):
        with self.lock:
            self.timings[name].append(elapsed)


active_counter: Counter | None = None


class TimedCursor:
    def __init__(self, cursor): self.cursor = cursor
    def __enter__(self): self.cursor.__enter__(); return self
    def __exit__(self, *args): return self.cursor.__exit__(*args)
    def __getattr__(self, name): return getattr(self.cursor, name)
    def execute(self, query, *args, **kwargs):
        started = perf_counter()
        try:
            self.cursor.execute(query, *args, **kwargs)
            return self
        finally:
            if active_counter is not None:
                active_counter.record("healthRoundTrip" if query == "" else "applicationQuery", (perf_counter() - started) * 1_000)


class TimedConnection(provider._SafeConnection):
    @classmethod
    def connect(cls, *args, **kwargs):
        started = perf_counter()
        try: return super().connect(*args, **kwargs)
        finally:
            if active_counter is not None: active_counter.record("connect", (perf_counter() - started) * 1_000)
    def cursor(self, *args, **kwargs): return TimedCursor(super().cursor(*args, **kwargs))


def distribution(values):
    values = sorted(values)
    return {"count": len(values), "p50Ms": round(values[max(0, math.ceil(len(values)*.5)-1)], 3) if values else None,
            "p95Ms": round(values[max(0, math.ceil(len(values)*.95)-1)], 3) if values else None,
            "totalMs": round(sum(values), 3)}


def run(output: Path, samples: int):
    global active_counter
    dsn = os.environ.get("OFFERSTEADY_STATE_READ_TEST_DATABASE_URL", "")
    validate_local_dsn(dsn)
    fixture = persistent_repositories.__wrapped__()
    settings, auth, sessions, _, user, auth_session, _, session = next(fixture)
    expected_auth = auth.get_access_token_state(auth_session_id=auth_session.auth_session_id, user_id=user.user_id)
    expected_session = sessions.get_control_state(session.session_id)
    original_connect = psycopg.connect
    original_class = provider._SafeConnection
    results = []
    try:
        psycopg.connect = TimedConnection.connect
        provider._SafeConnection = TimedConnection
        for concurrency in [1, 4, 8]:
            for pooled in [False, True]:
                candidate_settings = settings.model_copy(update={"cn_hot_database_pool_enabled": pooled,
                    "cn_hot_database_pool_max_size": 4, "cn_hot_database_pool_max_waiting": 16,
                    "cn_hot_database_pool_timeout_seconds": 3})
                auth.settings = sessions.settings = candidate_settings
                active_counter = Counter()
                activation = None
                def operation(_index=0):
                    started = perf_counter()
                    try:
                        state = auth.get_access_token_state(auth_session_id=auth_session.auth_session_id, user_id=user.user_id)
                        control = sessions.get_control_state(session.session_id)
                        assert state == expected_auth and control == expected_session
                        return {"elapsed": (perf_counter()-started)*1_000, "error": None}
                    except Exception as exc:
                        return {"elapsed": (perf_counter()-started)*1_000, "error": type(exc).__name__}
                try:
                    warm_started = perf_counter()
                    if pooled:
                        activation = provider.activate_cn_hot_database(candidate_settings)
                        # Measure startup separately and warm the bounded pool;
                        # no application read is hidden in pool construction.
                        with ExitStack() as stack:
                            for _ in range(4): stack.enter_context(auth._connect())
                        deadline = monotonic()+2
                        while provider.cn_hot_database_diagnostics(candidate_settings)["pool"].get("pool_available") != 4:
                            if monotonic() > deadline: raise RuntimeError("synthetic_pool_warmup_timeout")
                            sleep(.005)
                    assert operation()["error"] is None
                    warm_ms = (perf_counter()-warm_started)*1_000
                    warm_connects = len(active_counter.timings["connect"])
                    before = provider.cn_hot_database_diagnostics(candidate_settings) if pooled else None
                    active_counter = Counter()
                    wall_started = perf_counter()
                    with ThreadPoolExecutor(max_workers=concurrency) as executor:
                        completed = list(executor.map(operation, range(samples)))
                    wall_ms = (perf_counter()-wall_started)*1_000
                    measured = active_counter
                    after = provider.cn_hot_database_diagnostics(candidate_settings) if pooled else None
                    errors = [row["error"] for row in completed if row["error"]]
                    borrow = None
                    if pooled:
                        borrow = {key: {
                            "acquired": after["components"][key]["acquired"] - before["components"][key]["acquired"],
                            "acquireTotalMs": round(after["components"][key]["acquireTotalMs"] - before["components"][key]["acquireTotalMs"], 3),
                            "includesPoolWaitAndHealthCheck": True,
                        } for key in ["authentication", "sessions"]}
                    result = {"method": "bounded_pool" if pooled else "short_connection", "concurrency": concurrency,
                        "samples": samples, "errors": len(errors), "errorClasses": sorted(set(errors)),
                        "operation": distribution([row["elapsed"] for row in completed]),
                        "physicalConnect": distribution(measured.timings["connect"]),
                        "applicationQuery": distribution(measured.timings["applicationQuery"]),
                        "healthRoundTrip": distribution(measured.timings["healthRoundTrip"]),
                        "warmupAndStartupMs": round(warm_ms, 3), "warmupPhysicalConnections": warm_connects,
                        "wallMs": round(wall_ms, 3), "borrowMetrics": borrow,
                        "maxSize": 4 if pooled else None, "outputEquivalent": not errors}
                    assert not errors and len(measured.timings["applicationQuery"]) == samples * 2
                    if pooled:
                        assert len(measured.timings["healthRoundTrip"]) == samples * 2
                        assert after["pool"]["pool_size"] <= 4
                    else: assert len(measured.timings["connect"]) == samples * 2
                    results.append(result)
                finally:
                    provider.release_cn_hot_database(activation)
                    active_counter = None
        report = {"experiment": "actual_cn_auth_and_control_repository_reads", "passed": True,
            "samplesPerCell": samples, "results": results,
            "healthCheckImplementation": "psycopg_pool 3.3.3 executes an empty query per checkout, not SELECT 1; counted separately.",
            "queryMeasurement": "Test-only driver/cursor proxies time execute calls without retaining query text, parameters, IDs or returned bodies.",
            "limitations": ["Local synthetic loopback PostgreSQL; not production API P95.",
                "Each logical operation is one authoritative auth state SELECT and one control projection SELECT; billing/document/worker connections remain out of scope.",
                "Warm pool connection creation and first operation are reported separately; measurement does not hide health-check round trips.",
                "Timing includes Python scheduling and shared local resource variation; execute timing is not server-exclusive SQL CPU time.",
                "Pool borrow timing includes pool waiting, connection establishment when needed and checkout health check; it is not a pure queue metric."]}
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(json.dumps(report, indent=2)+"\n")
        return report
    finally:
        active_counter = None
        psycopg.connect = original_connect
        provider._SafeConnection = original_class
        try: next(fixture)
        except StopIteration: pass


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--samples", type=int, default=120)
    args = parser.parse_args()
    if not 20 <= args.samples <= 500: raise ValueError("bounded_synthetic_samples_required")
    result = run(args.output, args.samples)
    print(json.dumps({"passed": result["passed"], "cells": len(result["results"]),
        "samplesPerCell": result["samplesPerCell"], "errors": sum(cell["errors"] for cell in result["results"])}))
