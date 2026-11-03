"""Sample private timings for the CN device-status business job only.

The caller selects the CN route. Authentication dependencies, HTTP transport and
browser rendering precede/follow this scope and are not measured here. Repository
phases include serialization and are not pure Redis network timings. Phase totals
can be nested; they must not be summed to infer the whole request duration.
"""
from __future__ import annotations

from contextlib import contextmanager
from contextvars import ContextVar
from dataclasses import dataclass, field
import json
import logging
from math import isfinite
from threading import Lock
from time import perf_counter
from typing import Callable, Iterator, TypeVar

from fastapi import Request

from app.services.realtime_control_executor import run_realtime_control


T = TypeVar("T")
_SAMPLE_EVERY = 20
_PHASES = (
    "db_acquire", "db_execute", "db_fetch", "binding_repository", "event_repository",
)
_logger = logging.getLogger("offersteady.backend.cn_device_status_timing")
_sample_lock = Lock()
_sample_counter = 0


def _now() -> float | None:
    try:
        value = perf_counter()
        return value if isfinite(value) else None
    except Exception:
        return None


def _elapsed_ms(started: float | None, ended: float | None) -> float:
    if started is None or ended is None:
        return 0.0
    value = (ended - started) * 1_000
    return value if isfinite(value) and value >= 0 else 0.0


def _should_sample() -> bool:
    global _sample_counter
    try:
        with _sample_lock:
            _sample_counter = (_sample_counter + 1) % _SAMPLE_EVERY
            return _sample_counter == 0
    except Exception:
        return False


@dataclass
class _Trace:
    totals: dict[str, float] = field(default_factory=lambda: dict.fromkeys(_PHASES, 0.0))
    counts: dict[str, int] = field(default_factory=lambda: dict.fromkeys(_PHASES, 0))

    def record(self, phase: str, elapsed: float) -> None:
        # Only these five fields can ever grow, and only for one business job.
        total = self.totals[phase] + elapsed
        self.totals[phase] = total if isfinite(total) else self.totals[phase]
        self.counts[phase] = min(self.counts[phase] + 1, 2_147_483_647)


_current_trace: ContextVar[_Trace | None] = ContextVar("cn_device_status_trace", default=None)


@contextmanager
def measure_device_status_phase(phase: str) -> Iterator[None]:
    """A no-op outside the selected worker; never inspect the operation's data."""
    trace = None
    started = None
    try:
        if phase in _PHASES:
            trace = _current_trace.get()
            if trace is not None:
                started = _now()
    except Exception:
        trace = None
    try:
        yield
    finally:
        if trace is not None:
            try:
                trace.record(phase, _elapsed_ms(started, _now()))
            except Exception:
                pass


def _emit(trace: _Trace, *, queue_ms: float, work_ms: float, worker_failed: int) -> None:
    # Fixed labels and numerical values only. Never add kwargs, identifiers,
    # exception text, SQL, payloads or connection settings to this event.
    try:
        payload: dict[str, int | float] = {
            "schema": 1,
            "sample_every": _SAMPLE_EVERY,
            "queue_ms": round(queue_ms, 3),
            "work_ms": round(work_ms, 3),
            "worker_failed": worker_failed,
        }
        for phase in _PHASES:
            payload[f"{phase}_ms"] = round(trace.totals[phase], 3)
            payload[f"{phase}_count"] = trace.counts[phase]
        _logger.info("cn_device_status_timing %s", json.dumps(payload, separators=(",", ":"), allow_nan=False))
    except Exception:
        pass


async def run_cn_device_status_control(
    request: Request,
    operation: Callable[..., T],
    **kwargs: object,
) -> T:
    """Use the existing executor once, explicitly scoping its worker context.

    A cancelled await does not replay the operation. If a worker already started,
    its eventual sample describes that worker's result, not the HTTP outcome.
    """
    sampled = _should_sample()
    enqueued_at = _now() if sampled else None

    def invoke() -> T:
        trace = None
        token = None
        try:
            trace = _Trace() if sampled else None
        except Exception:
            trace = None
        try:
            # run_in_executor does not copy contextvars. Clear inherited context
            # for the existing asyncio.to_thread fallback and unselected jobs too.
            token = _current_trace.set(trace)
        except Exception:
            trace = None
        started_at = _now() if trace is not None else None
        failed = 0
        try:
            return operation(**kwargs)
        except BaseException:
            failed = 1
            raise
        finally:
            try:
                if trace is not None:
                    _emit(trace, queue_ms=_elapsed_ms(enqueued_at, started_at),
                          work_ms=_elapsed_ms(started_at, _now()), worker_failed=failed)
            except Exception:
                pass
            finally:
                if token is not None:
                    try:
                        _current_trace.reset(token)
                    except Exception:
                        pass

    return await run_realtime_control(request, invoke)
