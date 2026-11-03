"""Bounded CN voice I/O lanes; caller cancellation drains admitted work once."""
from __future__ import annotations

import asyncio
from concurrent.futures import Future, ThreadPoolExecutor
from dataclasses import dataclass
import json
import logging
from math import isfinite
import threading
from time import perf_counter
from typing import Callable, TypeVar


T = TypeVar("T")
_OPERATIONS = frozenset({
    "publisher_prepare", "publisher_create", "publisher_connect", "publisher_disconnect",
    "ingest_bootstrap", "ingest_frame", "legacy_frame", "legacy_ws_frame", "terminal_check",
    "capture_control",
    "session_end", "session_supersede",
})
_LANES = frozenset({"ingress", "lifecycle"})
_logger = logging.getLogger("offersteady.backend.cn_realtime_io_timing")
_sample_lock = threading.Lock()
_sample_counter = 0


def _should_sample() -> bool:
    global _sample_counter
    try:
        with _sample_lock:
            _sample_counter = (_sample_counter + 1) % 20
            return _sample_counter == 0
    except Exception:
        return False


def _now() -> float | None:
    try:
        value = perf_counter()
        return value if isfinite(value) else None
    except Exception:
        return None


def _elapsed(start: float | None, end: float | None) -> float:
    if start is None or end is None:
        return 0.0
    value = (end - start) * 1000
    return value if isfinite(value) and value >= 0 else 0.0


@dataclass
class _Timing:
    lane: str
    operation: str
    enqueued: float | None
    started: float | None = None
    finished: float | None = None


def _timing(lane: str, operation: str) -> _Timing | None:
    try:
        return _Timing(lane, operation, _now()) if _should_sample() else None
    except Exception:
        return None


def _invoke(operation: Callable[..., T], kwargs: dict[str, object], timing: _Timing | None) -> T:
    if timing is not None:
        timing.started = _now()
    try:
        return operation(**kwargs)
    finally:
        if timing is not None:
            timing.finished = _now()


def _emit(timing: _Timing | None, *, resumed: float | None, failed: bool, abandoned: bool, cleanup_failed: bool) -> None:
    if timing is None:
        return
    try:
        payload = {"schema": 1, "sample_every": 20, "lane": timing.lane, "operation": timing.operation,
                   "queue_ms": round(_elapsed(timing.enqueued, timing.started), 3),
                   "work_ms": round(_elapsed(timing.started, timing.finished), 3),
                   "resume_ms": round(_elapsed(timing.finished, resumed), 3),
                   "failed": int(failed), "abandoned": int(abandoned), "cleanup_failed": int(cleanup_failed)}
        _logger.info("cn_realtime_io_timing %s", json.dumps(payload, separators=(",", ":"), allow_nan=False))
    except Exception:
        pass


async def _drain(future: asyncio.Future[T]) -> tuple[T | None, BaseException | None, asyncio.CancelledError | None]:
    """Repeated cancellation never cancels, resubmits, or skips admitted work."""
    abandoned = None
    while True:
        try:
            return await asyncio.shield(future), None, abandoned
        except asyncio.CancelledError as error:
            if future.cancelled():
                return None, error, abandoned
            if future.done():
                try:
                    value = future.result()
                except BaseException as work_error:
                    return None, work_error, abandoned or (error if work_error is not error else None)
                return value, None, abandoned or error
            abandoned = abandoned or error
        except BaseException as error:
            return None, error, abandoned


async def _finish(
    future: asyncio.Future[T], timing: _Timing | None,
    cleanup: Callable[[T], object] | None,
    cleanup_runner: Callable[..., object],
) -> T:
    result, error, abandoned = await _drain(future)
    resumed = _now() if timing is not None else None
    cleanup_failed = False
    if abandoned and error is None and cleanup is not None:
        try:
            cleanup_task = asyncio.create_task(cleanup_runner(cleanup, result))
            _, cleanup_error, _ = await _drain(cleanup_task)
            if cleanup_error is not None:
                raise cleanup_error
        except BaseException:
            # Preserve caller cancellation. The callback is attempted once only;
            # do not replay resource creation or cleanup on transport failure.
            cleanup_failed = True
            try:
                _logger.warning('cn_realtime_io_cleanup_failed {"count":1}')
            except Exception:
                pass
    _emit(timing, resumed=resumed, failed=error is not None,
          abandoned=abandoned is not None, cleanup_failed=cleanup_failed)
    if abandoned:
        raise abandoned
    if error is not None:
        raise error
    return result  # type: ignore[return-value]


class _Lane:
    def __init__(self, *, workers: int, queue_max: int, name: str) -> None:
        self._workers = max(1, workers)
        self._queue_max = max(0, queue_max)
        self._pool = ThreadPoolExecutor(max_workers=self._workers, thread_name_prefix=f"cn-realtime-{name}")
        self._capacity = self._workers + self._queue_max
        self._reserved = 0
        self._admission = asyncio.Condition()
        self._lock = threading.Lock()
        self._futures: set[Future] = set()
        self._protected: set[Future] = set()
        self._loop: asyncio.AbstractEventLoop | None = None
        self._closed = False
        self._waiting = 0
        self._submitted = 0
        self._completed = 0
        self._active = 0
        self._max_active = 0
        self._max_pending = 0
        self._saturated = 0

    def _work(self, operation, kwargs, timing):
        with self._lock:
            self._active += 1
            self._max_active = max(self._max_active, self._active)
        try:
            return _invoke(operation, kwargs, timing)
        finally:
            with self._lock:
                self._active -= 1

    def _done(self, future: Future, loop: asyncio.AbstractEventLoop) -> None:
        with self._lock:
            self._futures.discard(future)
            self._protected.discard(future)
            self._completed += 1
        try:
            loop.call_soon_threadsafe(lambda: asyncio.create_task(self._release()))
        except RuntimeError:
            pass  # An already-closed loop cannot accept new requests.

    async def _release(self):
        async with self._admission:
            self._reserved -= 1
            self._admission.notify_all()

    async def _notify_closed(self):
        async with self._admission:
            self._admission.notify_all()

    async def submit(self, operation, kwargs, timing, *, internal=False):
        loop = asyncio.get_running_loop()
        async with self._admission:
            with self._lock:
                self._loop = loop
                self._waiting += 1
                if self._reserved >= self._capacity:
                    self._saturated += 1
            try:
                while self._reserved >= self._capacity:
                    if self._closed and not internal:
                        raise RuntimeError("CN realtime I/O executor is closed")
                    await self._admission.wait()
                if self._closed and not internal:
                    raise RuntimeError("CN realtime I/O executor is closed")
                self._reserved += 1
            finally:
                with self._lock:
                    self._waiting -= 1
        try:
            with self._lock:
                if self._closed and not internal:
                    raise RuntimeError("CN realtime I/O executor is closed")
                future = self._pool.submit(self._work, operation, kwargs, timing)
                self._futures.add(future)
                if internal:
                    self._protected.add(future)
                self._submitted += 1
                self._max_pending = max(self._max_pending, self._submitted - self._completed)
        except BaseException:
            await self._release()
            raise
        future.add_done_callback(lambda completed: self._done(completed, loop))
        return asyncio.wrap_future(future, loop=loop)

    def diagnostics(self) -> dict[str, int]:
        with self._lock:
            return {"submitted": self._submitted, "completed": self._completed, "active": self._active,
                    "pending": self._submitted - self._completed, "waiting": self._waiting,
                    "maxActive": self._max_active, "maxPending": self._max_pending,
                    "saturated": self._saturated, "configuredWorkers": self._workers,
                    "configuredQueueMax": self._queue_max, "closed": int(self._closed)}

    def stop_admission(self) -> None:
        with self._lock:
            if self._closed:
                return
            self._closed = True
            loop = self._loop
            cancellable = list(self._futures - self._protected)
        for future in cancellable:
            future.cancel()
        # Notification changes no capacity. Cancelled admission waiters cannot
        # refund artificial permits and expand the compensation queue.
        if loop is not None:
            try:
                loop.call_soon_threadsafe(lambda: asyncio.create_task(self._notify_closed()))
            except RuntimeError:
                pass

    def shutdown_pool(self) -> None:
        self._pool.shutdown(wait=False, cancel_futures=True)


class CnRealtimeIoExecutor:
    def __init__(self, *, ingress_workers: int = 4, ingress_queue_max: int = 16,
                 lifecycle_workers: int = 2, lifecycle_queue_max: int = 8) -> None:
        self._lanes = {
            "ingress": _Lane(workers=ingress_workers, queue_max=ingress_queue_max, name="ingress"),
            "lifecycle": _Lane(workers=lifecycle_workers, queue_max=lifecycle_queue_max, name="lifecycle"),
        }
        self._lock = threading.Lock()
        self._closed = False
        self._leases = 0
        self._pools_closed = False
        self._cleanup_failed = 0

    async def run(self, operation: Callable[..., T], *, lane: str = "ingress", operation_name: str,
                  on_abandoned_result: Callable[[T], object] | None = None, **kwargs: object) -> T:
        _validate(lane, operation_name)
        with self._lock:
            if self._closed:
                raise RuntimeError("CN realtime I/O executor is closed")
            self._leases += 1
        try:
            timing = _timing(lane, operation_name)
            future = await self._lanes[lane].submit(operation, dict(kwargs), timing)
            async def cleanup(callback, result):
                try:
                    observed = _timing("lifecycle", "publisher_disconnect")
                    cleaned = await self._lanes["lifecycle"].submit(lambda: callback(result), {}, observed, internal=True)
                    await _finish(cleaned, observed, None, None)
                except BaseException:
                    with self._lock:
                        self._cleanup_failed += 1
                    raise
            return await _finish(future, timing, on_abandoned_result, cleanup)
        finally:
            with self._lock:
                self._leases -= 1
            self._finish_shutdown_if_drained()

    def diagnostics(self) -> dict[str, object]:
        with self._lock:
            summary = {"cleanupFailed": self._cleanup_failed, "outstanding": self._leases,
                       "closing": int(self._closed), "poolsClosed": int(self._pools_closed)}
        return {**{name: lane.diagnostics() for name, lane in self._lanes.items()}, **summary}

    def _finish_shutdown_if_drained(self) -> None:
        with self._lock:
            if not self._closed or self._leases or self._pools_closed:
                return
            self._pools_closed = True
        for lane in self._lanes.values():
            lane.shutdown_pool()

    def shutdown(self) -> None:
        with self._lock:
            if self._closed:
                return
            self._closed = True
        for lane in self._lanes.values():
            lane.stop_admission()
        # Reserved compensation remains bounded and available until every
        # admitted owner has drained. New ordinary work never bypasses closure.
        self._finish_shutdown_if_drained()


def _validate(lane: str, operation_name: str) -> None:
    if lane not in _LANES or operation_name not in _OPERATIONS:
        raise ValueError("Unknown CN realtime I/O operation")


async def drain_cn_realtime_cleanup(operation) -> object:
    """A cleanup obligation cannot be skipped by another caller cancellation."""
    task = asyncio.create_task(operation)
    result, error, abandoned = await _drain(task)
    if error is not None:
        raise error
    if abandoned:
        raise abandoned
    return result


async def run_cn_realtime_io(surface, operation: Callable[..., T], *, lane: str = "ingress",
                             operation_name: str, on_abandoned_result: Callable[[T], object] | None = None,
                             **kwargs: object) -> T:
    _validate(lane, operation_name)
    try:
        executor = getattr(surface.app.state, "cn_realtime_io_executor", None)
    except (AttributeError, KeyError):
        executor = None
    if isinstance(executor, CnRealtimeIoExecutor):
        return await executor.run(operation, lane=lane, operation_name=operation_name,
                                  on_abandoned_result=on_abandoned_result, **kwargs)
    timing = _timing(lane, operation_name)
    future = asyncio.create_task(asyncio.to_thread(_invoke, operation, dict(kwargs), timing))
    async def cleanup(callback, result):
        task = asyncio.create_task(asyncio.to_thread(callback, result))
        _, error, _ = await _drain(task)
        if error is not None:
            raise error
    return await _finish(future, timing, on_abandoned_result, cleanup)
