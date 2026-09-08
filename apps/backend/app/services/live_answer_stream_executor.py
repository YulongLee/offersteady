from __future__ import annotations

import asyncio
import threading
from collections.abc import AsyncIterator, Callable, Iterator
from concurrent.futures import TimeoutError as FutureTimeoutError
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from time import time


@dataclass(frozen=True)
class _StreamMessage:
    frame: str | None = None
    error: Exception | None = None
    terminal: bool = False


class LiveAnswerStreamLease:
    def __init__(self, owner: "LiveAnswerStreamExecutor", *, admitted_at_ms: int) -> None:
        self._owner = owner
        self._released = False
        self._lock = threading.Lock()
        self.admitted_at_ms = admitted_at_ms

    def release(self) -> None:
        with self._lock:
            if self._released:
                return
            self._released = True
        self._owner._release_slot()


class LiveAnswerStreamExecutor:
    """Run synchronous answer iterators outside Starlette's shared worker pool."""

    def __init__(self, *, max_workers: int, queue_max: int, event_queue_max: int) -> None:
        self._max_workers = max(1, max_workers)
        self._queue_max = max(0, queue_max)
        self._event_queue_max = max(1, event_queue_max)
        self._executor = ThreadPoolExecutor(
            max_workers=self._max_workers,
            thread_name_prefix="live-answer-stream",
        )
        self._slots = threading.BoundedSemaphore(self._max_workers + self._queue_max)
        self._lock = threading.Lock()
        self._submitted = 0
        self._completed = 0
        self._active = 0
        self._max_active = 0
        self._max_pending = 0
        self._saturated = 0
        self._closed = False

    def available(self) -> bool:
        with self._lock:
            return not self._closed

    def try_acquire(self) -> LiveAnswerStreamLease | None:
        with self._lock:
            if self._closed:
                self._saturated += 1
                return None
        if not self._slots.acquire(blocking=False):
            with self._lock:
                self._saturated += 1
            return None
        admitted_at_ms = int(time() * 1_000)
        with self._lock:
            if self._closed:
                self._slots.release()
                self._saturated += 1
                return None
            self._submitted += 1
            pending = max(0, self._submitted - self._completed - self._active)
            self._max_pending = max(self._max_pending, pending)
        return LiveAnswerStreamLease(self, admitted_at_ms=admitted_at_ms)

    def _release_slot(self) -> None:
        self._slots.release()

    def _mark_started(self) -> None:
        with self._lock:
            self._active += 1
            self._max_active = max(self._max_active, self._active)

    def _mark_completed(self) -> None:
        with self._lock:
            self._active = max(0, self._active - 1)
            self._completed += 1

    async def stream(
        self,
        lease: LiveAnswerStreamLease,
        producer_factory: Callable[[], Iterator[str]],
    ) -> AsyncIterator[str]:
        loop = asyncio.get_running_loop()
        queue: asyncio.Queue[_StreamMessage] = asyncio.Queue(maxsize=self._event_queue_max)
        stop = threading.Event()

        def deliver(message: _StreamMessage) -> bool:
            while not stop.is_set():
                delivery = asyncio.run_coroutine_threadsafe(queue.put(message), loop)
                try:
                    delivery.result(timeout=0.1)
                    return True
                except FutureTimeoutError:
                    if not delivery.cancel():
                        delivery.result()
                        return True
            return False

        def produce() -> None:
            iterator: Iterator[str] | None = None
            self._mark_started()
            try:
                iterator = producer_factory()
                for frame in iterator:
                    if stop.is_set() or not deliver(_StreamMessage(frame=frame)):
                        break
                if not stop.is_set():
                    deliver(_StreamMessage(terminal=True))
            except Exception as exc:
                if not stop.is_set():
                    deliver(_StreamMessage(error=exc))
            finally:
                try:
                    if stop.is_set() and iterator is not None:
                        close = getattr(iterator, "close", None)
                        if callable(close):
                            close()
                finally:
                    self._mark_completed()
                    lease.release()

        try:
            loop.run_in_executor(self._executor, produce)
        except Exception:
            lease.release()
            raise

        try:
            while True:
                message = await queue.get()
                if message.error is not None:
                    raise message.error
                if message.terminal:
                    return
                if message.frame is not None:
                    yield message.frame
        finally:
            stop.set()

    def diagnostics(self) -> dict[str, int]:
        with self._lock:
            return {
                "submitted": self._submitted,
                "completed": self._completed,
                "active": self._active,
                "pending": max(0, self._submitted - self._completed - self._active),
                "maxActive": self._max_active,
                "maxPending": self._max_pending,
                "saturated": self._saturated,
                "configuredWorkers": self._max_workers,
                "configuredQueueMax": self._queue_max,
                "configuredEventQueueMax": self._event_queue_max,
            }

    def shutdown(self) -> None:
        with self._lock:
            if self._closed:
                return
            self._closed = True
        self._executor.shutdown(wait=False, cancel_futures=True)
