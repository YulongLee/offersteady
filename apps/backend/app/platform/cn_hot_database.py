"""Explicit CN Backend-only connection reuse; never a data or auth cache.

Only the authentication and session repositories opt into this provider. Their
SQL must not change session-level PostgreSQL settings. The existing transaction
contexts remain authoritative; failed application statements are never replayed.
"""
from __future__ import annotations

import asyncio
from contextlib import asynccontextmanager, contextmanager
from dataclasses import dataclass, field
from hashlib import sha256
import json
import os
from threading import Lock
from time import perf_counter
from typing import Any, Iterator, Literal

import psycopg
from psycopg.rows import tuple_row

from app.core.config import Settings


Component = Literal["authentication", "sessions"]


class _SafeConnection(psycopg.Connection):
    @classmethod
    def connect(cls, *args: Any, **kwargs: Any):
        try:
            return super().connect(*args, **kwargs)
        except Exception:
            # The pool logs background connect failures. Do not let connection
            # strings or provider error details enter those new diagnostics.
            raise psycopg.OperationalError("cn_hot_database_connect_failed") from None


@dataclass(frozen=True, repr=False)
class _Configuration:
    dsn: str
    connect_timeout: float
    application_name: str
    max_size: int
    max_waiting: int
    timeout: float

    @property
    def identity(self) -> str:
        return sha256(json.dumps([
            self.dsn, self.connect_timeout, self.application_name,
            self.max_size, self.max_waiting, self.timeout,
        ], separators=(",", ":")).encode()).hexdigest()


@dataclass(repr=False)
class _Entry:
    configuration: _Configuration
    pool: Any
    pid: int
    references: int = 1
    closed: bool = False
    loans: int = 0
    pool_closed: bool = False
    metrics_lock: Any = field(default_factory=Lock)
    metrics: dict[str, dict[str, int | float]] = field(default_factory=lambda: {
        key: {"acquired": 0, "acquireErrors": 0, "acquireTotalMs": 0.0,
              "acquireMaxMs": 0.0, "active": 0}
        for key in ("authentication", "sessions")
    })


@dataclass(repr=False)
class _Activation:
    entry: _Entry
    released: bool = False


_lock = Lock()
_pid = os.getpid()
_entry: _Entry | None = None
_retiring: _Entry | None = None
_closed_identities: set[str] = set()
# A fork must neither borrow nor send a shutdown protocol to its parent's pool.
# Keep inherited objects unreachable by the provider, without calling close().
_inherited_entries: list[_Entry] = []


def _after_fork() -> None:
    global _lock, _pid, _entry, _retiring, _closed_identities
    if _entry is not None:
        _inherited_entries.append(_entry)
    if _retiring is not None:
        _inherited_entries.append(_retiring)
    _lock = Lock()
    _pid = os.getpid()
    _entry = None
    _retiring = None
    _closed_identities = set()


if hasattr(os, "register_at_fork"):
    os.register_at_fork(after_in_child=_after_fork)


def _check_pid() -> None:
    if os.getpid() != _pid:
        _after_fork()


def _configuration(settings: Settings) -> _Configuration | None:
    if settings.product_edition != "cn" or not settings.cn_hot_database_pool_enabled:
        return None
    if not settings.database_url:
        raise RuntimeError("cn_hot_database_url_required")
    return _Configuration(
        dsn=settings.database_url,
        connect_timeout=settings.database_connect_timeout_seconds,
        application_name=f"{settings.database_application_name}-cn-hot",
        max_size=settings.cn_hot_database_pool_max_size,
        max_waiting=settings.cn_hot_database_pool_max_waiting,
        timeout=settings.cn_hot_database_pool_timeout_seconds,
    )


def _reset_connection(connection: psycopg.Connection) -> None:
    # These two repositories only select cursor-level row factories. If future
    # code changes connection-level Python state, discard it instead of leaking
    # that state to a different request. Do not RESET ALL/alter DSN options.
    if (connection.autocommit or connection.row_factory is not tuple_row
            or connection.isolation_level is not None
            or connection.read_only is not None or connection.deferrable is not None):
        connection.close()


def activate_cn_hot_database(settings: Settings) -> _Activation | None:
    """Called only by the Backend lifespan (or isolated tests), never on import."""
    global _entry
    configuration = _configuration(settings)
    if configuration is None:
        return None
    _check_pid()
    with _lock:
        if _retiring is not None:
            raise RuntimeError("cn_hot_database_borrowers_returning")
        if _entry is not None:
            if _entry.configuration != configuration:
                raise RuntimeError("cn_hot_database_configuration_conflict")
            _entry.references += 1
            return _Activation(_entry)
        # Keep this import behind both the regional flag and explicit activation.
        from psycopg_pool import ConnectionPool

        pool = ConnectionPool(
            conninfo=configuration.dsn,
            connection_class=_SafeConnection,
            kwargs={"connect_timeout": configuration.connect_timeout,
                    "application_name": configuration.application_name},
            min_size=0, max_size=configuration.max_size,
            max_waiting=configuration.max_waiting, timeout=configuration.timeout,
            num_workers=min(3, configuration.max_size), open=False,
            check=ConnectionPool.check_connection, reset=_reset_connection,
            name="offersteady-cn-hot",
        )
        try:
            pool.open(wait=False)
        except BaseException:
            pool.close()
            raise
        _entry = _Entry(configuration, pool, os.getpid())
        _closed_identities.discard(configuration.identity)
        return _Activation(_entry)


def release_cn_hot_database(activation: _Activation | None) -> None:
    global _entry, _retiring
    if activation is None or activation.released:
        return
    # A child cannot close its parent's sockets or copied thread locks.
    if activation.entry.pid != os.getpid():
        activation.released = True
        return
    _check_pid()
    close = False
    with _lock:
        if activation.released:
            return
        activation.released = True
        current = activation.entry
        current.references -= 1
        if current.references == 0:
            current.closed = True
            if _entry is current:
                _entry = None
            _retiring = current
            _closed_identities.add(current.configuration.identity)
            close = True
    if close:
        try:
            current.pool.close()
        finally:
            with _lock:
                current.pool_closed = True
                if current.loans == 0 and _retiring is current:
                    _retiring = None


@contextmanager
def _borrow(entry: _Entry, component: Component) -> Iterator[psycopg.Connection]:
    global _retiring
    if entry.pid != os.getpid():
        raise RuntimeError("cn_hot_database_runtime_closed")
    with _lock:
        if entry.closed:
            raise RuntimeError("cn_hot_database_runtime_closed")
        entry.loans += 1
    started = perf_counter()
    acquired = False
    try:
        with entry.pool.connection(timeout=entry.configuration.timeout) as connection:
            elapsed = (perf_counter() - started) * 1_000
            with entry.metrics_lock:
                counters = entry.metrics[component]
                counters["acquired"] += 1
                counters["acquireTotalMs"] += elapsed
                counters["acquireMaxMs"] = max(counters["acquireMaxMs"], elapsed)
                counters["active"] += 1
            acquired = True
            yield connection
    except BaseException:
        if not acquired:
            with entry.metrics_lock:
                entry.metrics[component]["acquireErrors"] += 1
        raise
    finally:
        if acquired:
            with entry.metrics_lock:
                entry.metrics[component]["active"] -= 1
        with _lock:
            entry.loans -= 1
            if entry.closed and entry.pool_closed and entry.loans == 0 and _retiring is entry:
                _retiring = None


def cn_hot_repository_connection(settings: Settings, component: Component):
    """Return a loan context or None for the repository's original short path."""
    if component not in {"authentication", "sessions"}:
        raise ValueError("cn_hot_database_component_invalid")
    configuration = _configuration(settings)
    if configuration is None:
        return None
    _check_pid()
    with _lock:
        if _entry is None:
            if configuration.identity in _closed_identities:
                raise RuntimeError("cn_hot_database_runtime_closed")
            # A worker which only inherited the flag never activates this pool.
            return None
        if _entry.configuration != configuration:
            raise RuntimeError("cn_hot_database_configuration_conflict")
        return _borrow(_entry, component)


def cn_hot_database_diagnostics(settings: Settings) -> dict[str, Any]:
    configuration = _configuration(settings)
    if configuration is None:
        return {"active": False}
    _check_pid()
    with _lock:
        current = _entry
        if current is None or current.configuration != configuration:
            return {"active": False}
        with current.metrics_lock:
            components = {key: dict(value) for key, value in current.metrics.items()}
        return {"active": True, "references": current.references,
                "pool": current.pool.get_stats(), "components": components}


def with_cn_hot_database_lifespan(lifespan, settings: Settings):
    @asynccontextmanager
    async def managed(application):
        activation = activate_cn_hot_database(settings)
        try:
            async with lifespan(application):
                yield
        finally:
            # The outer context also covers errors before the original yield.
            await asyncio.to_thread(release_cn_hot_database, activation)
    return managed
