"""Local synthetic connection-reuse experiment, never product runtime code.

Requires the existing development Python/psycopg and a separately installed,
pinned psycopg_pool 3.3.3 supplied with --pool-module-dir. No DSN is written to
the report. Only the dedicated loopback synthetic database is accepted.
"""
from __future__ import annotations

import argparse
from collections.abc import Callable, Iterator
from concurrent.futures import ThreadPoolExecutor
from contextlib import contextmanager
from importlib import metadata
import json
import logging
import math
import os
from pathlib import Path
import platform
import sys
from threading import Event, Lock, Thread
from time import monotonic, perf_counter, sleep
from typing import Any
from uuid import uuid4

import psycopg
from psycopg import sql
from psycopg.conninfo import conninfo_to_dict
from psycopg.pq import TransactionStatus


DSN_ENV = "OFFERSTEADY_STATE_READ_TEST_DATABASE_URL"
EXPECTED_DATABASE = "synthetic_state"
EXPECTED_USER = "synthetic_state"
POOL_VERSION = "3.3.3"
DEFAULT_PORT = 58642
MAX_POOL_SIZE = 4
MAX_WAITING = 16
OPERATIONS_PER_SAMPLE = 3
FORBIDDEN_DATABASE_ENVIRONMENT = (
    "PGHOST", "PGHOSTADDR", "PGPORT", "PGDATABASE", "PGUSER",
    "PGSERVICE", "PGSERVICEFILE", "PGSYSCONFDIR", "PGPASSFILE",
    "PGTARGETSESSIONATTRS", "PGLOADBALANCEHOSTS",
)


def validate_local_dsn(dsn: str, *, expected_port: int = DEFAULT_PORT) -> str:
    """Reject implicit/service discovery and every destination except this test DB."""
    # Fail closed even for empty values: this standalone experiment accepts only
    # its explicit destination, never ambient libpq routing/service defaults.
    if any(key in os.environ for key in FORBIDDEN_DATABASE_ENVIRONMENT):
        raise ValueError("indirect_database_environment_forbidden")
    if not dsn:
        raise ValueError("explicit_synthetic_database_required")
    try:
        info = conninfo_to_dict(dsn)
    except Exception:
        raise ValueError("invalid_synthetic_database_configuration") from None
    if any(key in info for key in ("service", "servicefile", "hostaddr", "passfile")):
        raise ValueError("indirect_database_configuration_forbidden")
    if info.get("host") not in {"127.0.0.1", "localhost", "::1"}:
        raise ValueError("loopback_database_required")
    if info.get("dbname") != EXPECTED_DATABASE or info.get("user") != EXPECTED_USER:
        raise ValueError("dedicated_synthetic_database_required")
    if not 1024 <= expected_port <= 65535 or info.get("port") != str(expected_port):
        raise ValueError("dedicated_synthetic_port_required")
    return dsn


def percentile(values: list[float], fraction: float) -> float:
    ordered = sorted(values)
    return round(ordered[max(0, math.ceil(len(ordered) * fraction) - 1)], 3)


class WorkCounter:
    def __init__(self) -> None:
        self.lock = Lock()
        self.created = 0
        self.borrowed = 0
        self.peak_borrowed = 0

    def connected(self, _connection: psycopg.Connection | None = None) -> None:
        with self.lock:
            self.created += 1

    @contextmanager
    def borrowing(self) -> Iterator[None]:
        with self.lock:
            self.borrowed += 1
            self.peak_borrowed = max(self.peak_borrowed, self.borrowed)
        try:
            yield
        finally:
            with self.lock:
                self.borrowed -= 1


def load_pool_module(module_dir: Path):
    if not module_dir.is_absolute() or not module_dir.is_dir():
        raise ValueError("explicit_isolated_pool_module_directory_required")
    sys.path.insert(0, str(module_dir))
    import psycopg_pool
    if metadata.version("psycopg_pool") != POOL_VERSION:
        raise ValueError("unexpected_pool_dependency_version")
    if module_dir.resolve() not in Path(psycopg_pool.__file__).resolve().parents:
        raise ValueError("pool_dependency_not_from_isolated_directory")
    logging.getLogger("psycopg.pool").setLevel(logging.CRITICAL)
    return psycopg_pool


def connect(dsn: str, app_name: str) -> psycopg.Connection:
    return psycopg.connect(
        dsn, connect_timeout=3, application_name=app_name,
        options="-c statement_timeout=3000 -c lock_timeout=1000",
    )


def connection_count(dsn: str, app_name: str) -> int:
    with connect(dsn, "synthetic-pool-eval-observer") as connection:
        return connection.execute(
            "SELECT COUNT(*) FROM pg_stat_activity "
            "WHERE datname=current_database() AND application_name=%s", (app_name,),
        ).fetchone()[0]


def wait_for_no_connections(dsn: str, app_name: str) -> bool:
    deadline = monotonic() + 2
    while monotonic() < deadline:
        if connection_count(dsn, app_name) == 0:
            return True
        sleep(0.01)
    return False


def make_pool(pool_module, dsn: str, app_name: str, *, size: int, max_waiting: int,
              counter: WorkCounter | None = None):
    return pool_module.ConnectionPool(
        conninfo=dsn,
        kwargs={"connect_timeout": 3, "application_name": app_name,
                "options": "-c statement_timeout=3000 -c lock_timeout=1000"},
        min_size=size, max_size=size, max_waiting=max_waiting, timeout=2,
        num_workers=1, open=False, configure=counter.connected if counter else None,
        name="synthetic-state-read-evaluation",
    )


def workload_case(pool_module, dsn: str, schema: str, *, method: str,
                  concurrency: int, samples: int) -> dict[str, Any]:
    counter = WorkCounter()
    app_name = f"synthetic-state-{method}-{uuid4().hex[:10]}"
    pool = None
    started = perf_counter()
    if method == "bounded_pool":
        pool = make_pool(pool_module, dsn, app_name, size=MAX_POOL_SIZE,
                         max_waiting=MAX_WAITING, counter=counter)
        pool.open(wait=True, timeout=5)
    startup_ms = (perf_counter() - started) * 1000

    @contextmanager
    def borrow():
        if pool is None:
            with connect(dsn, app_name) as connection:
                counter.connected()
                with counter.borrowing():
                    yield connection
        else:
            with pool.connection(timeout=2) as connection:
                with counter.borrowing():
                    yield connection

    statement = sql.SQL("SELECT owner_id, revision, ready FROM {}.documents "
                        "WHERE document_id=%s AND owner_id=%s").format(sql.Identifier(schema))

    def one_operation(index: int) -> tuple[float, str | None]:
        began = perf_counter()
        try:
            for offset in range(OPERATIONS_PER_SAMPLE):
                identifier = (index * OPERATIONS_PER_SAMPLE + offset) % 120
                owner = f"synthetic-owner-{identifier % 8}"
                with borrow() as connection:
                    record = connection.execute(statement, (identifier, owner)).fetchone()
                    if record != (owner, identifier % 5, True):
                        raise AssertionError("synthetic_read_mismatch")
            return (perf_counter() - began) * 1000, None
        except Exception as exc:
            # An exception string can contain DSN or SQL parameters: emit only its type.
            return (perf_counter() - began) * 1000, type(exc).__name__

    try:
        _, warmup_error = one_operation(0)
        if warmup_error:
            raise RuntimeError("synthetic_warmup_failed")
        warm_created = counter.created
        counter.peak_borrowed = 0
        began = perf_counter()
        with ThreadPoolExecutor(max_workers=concurrency) as executor:
            observed = list(executor.map(one_operation, range(samples)))
        wall_ms = (perf_counter() - began) * 1000
        durations = [duration for duration, _ in observed]
        errors = [error for _, error in observed if error]
        stats = pool.get_stats() if pool else None
        result = {
            "method": method, "concurrency": concurrency, "samples": samples,
            "queriesPerOperation": OPERATIONS_PER_SAMPLE,
            "successfulQueries": (samples - len(errors)) * OPERATIONS_PER_SAMPLE,
            "errors": len(errors), "errorTypes": sorted(set(errors)),
            "p50Ms": percentile(durations, .5), "p95Ms": percentile(durations, .95),
            "p99Ms": percentile(durations, .99), "wallMs": round(wall_ms, 3),
            "startupMs": round(startup_ms, 3),
            "connectionsCreatedDuringMeasuredOperations": counter.created - warm_created,
            "connectionsCreatedIncludingStartupAndWarmup": counter.created,
            "peakBorrowedConnections": counter.peak_borrowed,
            "borrowedAfterWorkload": counter.borrowed,
            "poolMaxSize": MAX_POOL_SIZE if pool else None,
            "poolMaxWaiting": MAX_WAITING if pool else None,
            "poolStatsAfterWorkload": stats,
        }
    finally:
        if pool is not None:
            pool.close(timeout=5)
    result["allConnectionsClosed"] = wait_for_no_connections(dsn, app_name)
    result["connectionsAfterClose"] = connection_count(dsn, app_name)
    result["resourceBoundsSatisfied"] = (
        result["peakBorrowedConnections"] <= (MAX_POOL_SIZE if pool else concurrency)
        and result["borrowedAfterWorkload"] == 0
        and (result["connectionsCreatedDuringMeasuredOperations"] == samples * OPERATIONS_PER_SAMPLE if pool is None else
             result["connectionsCreatedIncludingStartupAndWarmup"] <= MAX_POOL_SIZE
             and result["poolStatsAfterWorkload"].get("requests_waiting", 0) == 0
             and result["poolStatsAfterWorkload"].get("pool_size", 0) <= MAX_POOL_SIZE)
    )
    return result


class SyntheticRollback(Exception):
    pass


def lifecycle_checks(pool_module, dsn: str, schema: str) -> dict[str, Any]:
    name = f"synthetic-state-lifecycle-{uuid4().hex[:10]}"
    pool = make_pool(pool_module, dsn, name, size=1, max_waiting=1)
    pool.open(wait=True, timeout=5)
    outcomes: dict[str, Any] = {}
    insert = sql.SQL("INSERT INTO {}.transaction_probe VALUES (%s)").format(sql.Identifier(schema))
    count = sql.SQL("SELECT COUNT(*) FROM {}.transaction_probe").format(sql.Identifier(schema))
    try:
        try:
            with pool.connection() as connection:
                connection.execute(insert, (1,))
                raise SyntheticRollback()
        except SyntheticRollback:
            pass
        with pool.connection() as connection:
            outcomes["exceptionReturnedIdleConnection"] = connection.info.transaction_status == TransactionStatus.IDLE
            outcomes["exceptionWriteRolledBack"] = connection.execute(count).fetchone()[0] == 0
            connection.execute(insert, (2,))
        with pool.connection() as connection:
            outcomes["successCommitted"] = connection.execute(count).fetchone()[0] == 1

        try:
            with pool.connection() as connection:
                connection.execute("SELECT 1 / 0")
        except psycopg.errors.DivisionByZero:
            outcomes["expectedSqlErrorObserved"] = True
        with pool.connection() as connection:
            outcomes["sqlErrorReturnedIdleConnection"] = connection.info.transaction_status == TransactionStatus.IDLE
            outcomes["readAfterSqlErrorSucceeded"] = connection.execute("SELECT 1").fetchone() == (1,)

        with pool.connection():
            began = perf_counter()
            try:
                pool.getconn(timeout=0.04)
            except pool_module.PoolTimeout:
                outcomes["expectedAcquireTimeoutObserved"] = True
                outcomes["acquireTimeoutMs"] = round((perf_counter() - began) * 1000, 3)

        waiter_started = Event()
        waiter_errors: list[str] = []
        waiter_succeeded = Event()

        def waiter():
            waiter_started.set()
            try:
                with pool.connection(timeout=1) as connection:
                    if connection.execute("SELECT 1").fetchone() == (1,):
                        waiter_succeeded.set()
            except Exception as exc:
                waiter_errors.append(type(exc).__name__)

        with pool.connection():
            thread = Thread(target=waiter, name="synthetic-pool-eval-waiter")
            thread.start()
            if not waiter_started.wait(1):
                raise AssertionError("synthetic_waiter_not_started")
            deadline = monotonic() + 1
            while pool.get_stats().get("requests_waiting", 0) != 1 and monotonic() < deadline:
                sleep(.005)
            outcomes["singleWaiterQueued"] = pool.get_stats().get("requests_waiting", 0) == 1
            try:
                pool.getconn(timeout=.04)
            except pool_module.TooManyRequests:
                outcomes["expectedQueueBoundRejectionObserved"] = True
        thread.join(timeout=2)
        outcomes["queuedWaiterSucceededAfterRelease"] = waiter_succeeded.is_set() and not thread.is_alive()
        outcomes["unexpectedWaiterErrorCount"] = len(waiter_errors)
        outcomes["waitersAfterRelease"] = pool.get_stats().get("requests_waiting", 0)
    finally:
        pool.close(timeout=5)
    outcomes["poolClosed"] = pool.closed
    outcomes["allConnectionsClosed"] = wait_for_no_connections(dsn, name)
    try:
        pool.getconn(timeout=.04)
    except pool_module.PoolClosed:
        outcomes["closedPoolRejectsNewBorrow"] = True

    # Closing never tears down a connection still borrowed by a caller.
    held_name = f"synthetic-state-held-close-{uuid4().hex[:10]}"
    held_pool = make_pool(pool_module, dsn, held_name, size=1, max_waiting=1)
    held_pool.open(wait=True, timeout=5)
    try:
        with held_pool.connection() as held:
            held_pool.close(timeout=5)
            outcomes["closePreservesBorrowedConnectionUntilReturn"] = not held.closed and held.execute("SELECT 1").fetchone() == (1,)
    finally:
        held_pool.close(timeout=5)
    outcomes["borrowedConnectionClosedOnReturn"] = held.closed
    outcomes["heldPoolConnectionsClosedAfterReturn"] = wait_for_no_connections(dsn, held_name)
    required = [
        "exceptionReturnedIdleConnection", "exceptionWriteRolledBack", "successCommitted",
        "expectedSqlErrorObserved", "sqlErrorReturnedIdleConnection", "readAfterSqlErrorSucceeded",
        "expectedAcquireTimeoutObserved", "singleWaiterQueued", "expectedQueueBoundRejectionObserved",
        "queuedWaiterSucceededAfterRelease", "poolClosed", "allConnectionsClosed",
        "closedPoolRejectsNewBorrow", "closePreservesBorrowedConnectionUntilReturn",
        "borrowedConnectionClosedOnReturn", "heldPoolConnectionsClosedAfterReturn",
    ]
    outcomes["passed"] = all(outcomes.get(key) is True for key in required) and outcomes["unexpectedWaiterErrorCount"] == 0 and outcomes["waitersAfterRelease"] == 0
    return outcomes


def evaluate(dsn: str, pool_module, *, samples: int) -> dict[str, Any]:
    schema = f"synthetic_pool_eval_{uuid4().hex[:16]}"
    created = False
    results: list[dict[str, Any]] = []
    try:
        with connect(dsn, "synthetic-state-eval-setup") as connection:
            if connection.execute("SELECT current_database(), current_user").fetchone() != (EXPECTED_DATABASE, EXPECTED_USER):
                raise ValueError("unexpected_database_identity")
            server_version = connection.info.server_version
            connection.execute(sql.SQL("CREATE SCHEMA {}").format(sql.Identifier(schema)))
            connection.execute(sql.SQL("CREATE TABLE {}.documents (document_id INTEGER PRIMARY KEY, owner_id TEXT NOT NULL, revision INTEGER NOT NULL, ready BOOLEAN NOT NULL)").format(sql.Identifier(schema)))
            connection.execute(sql.SQL("CREATE TABLE {}.transaction_probe (value INTEGER PRIMARY KEY)").format(sql.Identifier(schema)))
            with connection.cursor() as cursor:
                cursor.executemany(sql.SQL("INSERT INTO {}.documents VALUES (%s,%s,%s,%s)").format(sql.Identifier(schema)), [(i, f"synthetic-owner-{i % 8}", i % 5, True) for i in range(120)])
        created = True
        # Alternate order to limit a systematic always-second timing advantage.
        for concurrency in (1, 4, 8):
            methods = ("short_connection", "bounded_pool") if concurrency != 4 else ("bounded_pool", "short_connection")
            for method in methods:
                results.append(workload_case(pool_module, dsn, schema, method=method, concurrency=concurrency, samples=samples))
        lifecycle = lifecycle_checks(pool_module, dsn, schema)
        passed = all(result["errors"] == 0 and result["resourceBoundsSatisfied"] and result["allConnectionsClosed"] and result["connectionsAfterClose"] == 0 for result in results) and lifecycle["passed"]
        return {
            "experiment": "synthetic-local-connection-reuse-only", "passed": passed,
            "databaseGuard": {"loopbackOnly": True, "dedicatedSyntheticDatabase": True, "randomSchema": True},
            "versions": {"python": platform.python_version(), "psycopg": metadata.version("psycopg"), "psycopgPool": metadata.version("psycopg_pool"), "postgresServerVersion": server_version},
            "method": {"samplesPerCell": samples, "concurrency": [1, 4, 8], "queriesPerLogicalOperation": OPERATIONS_PER_SAMPLE, "poolSize": MAX_POOL_SIZE, "poolMaxWaiting": MAX_WAITING, "poolAcquireTimeoutSeconds": 2, "identicalPointReadSql": True, "warmupOperationsPerCell": 1, "timingIncludesWaitingForPool": True, "poolStartupReportedSeparately": True},
            "results": results, "lifecycle": lifecycle,
            "sources": ["https://www.psycopg.org/psycopg3/docs/api/pool.html", "https://pypi.org/project/psycopg-pool/3.3.3/"],
            "limitations": [
                "Local loopback synthetic point reads isolate connection reuse; this is not an application replay or production API P95 forecast.",
                "Measured operation latency includes three connection acquisitions and identical point reads; pool startup is separate and counted.",
                "Docker resource limits and other local processes affect timing; no artificial remote network delay or pg_sleep is used in measured workloads.",
                "The experiment does not validate product auth revocation, request-scoped data freshness, all transaction usage patterns, production pool sizing, or multi-process lifecycle.",
                "Expected SQL/queue/timeout failures are lifecycle assertions, separate from zero-error normal workloads.",
                "The optional pool package is isolated test tooling; no runtime dependency, configuration, provider call, or production service is changed.",
            ],
        }
    finally:
        if created:
            with connect(dsn, "synthetic-state-eval-cleanup") as connection:
                connection.execute(sql.SQL("DROP SCHEMA {} CASCADE").format(sql.Identifier(schema)))


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--pool-module-dir", type=Path, required=True)
    parser.add_argument("--expected-port", type=int, default=DEFAULT_PORT)
    parser.add_argument("--samples", type=int, default=120)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if not 80 <= args.samples <= 150:
        raise ValueError("samples_must_be_between_80_and_150")
    dsn = validate_local_dsn(os.environ.get(DSN_ENV, ""), expected_port=args.expected_port)
    module = load_pool_module(args.pool_module_dir)
    result = evaluate(dsn, module, samples=args.samples)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n")
    print(json.dumps({"passed": result["passed"], "output": str(args.output), "cells": len(result["results"]), "normalWorkloadErrors": sum(row["errors"] for row in result["results"]), "lifecyclePassed": result["lifecycle"]["passed"]}))
    return 0 if result["passed"] else 1


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        print(json.dumps({"passed": False, "errorType": type(exc).__name__, "detail": "Local synthetic evaluation failed; DSN and exception text intentionally omitted."}))
        raise SystemExit(1) from None
