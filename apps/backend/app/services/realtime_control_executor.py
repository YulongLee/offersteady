from __future__ import annotations

import asyncio
import threading
from concurrent.futures import ThreadPoolExecutor
from functools import partial
from typing import Callable, TypeVar

from fastapi import Request


T = TypeVar("T")


class RealtimeControlExecutor:
    """Keep short synchronous realtime control work off the asyncio loop."""

    def __init__(self, *, max_workers: int, queue_max: int) -> None:
        workers = max(1, max_workers)
        self._executor = ThreadPoolExecutor(
            max_workers=workers,
            thread_name_prefix="realtime-control",
        )
        self._slots = asyncio.Semaphore(workers + max(1, queue_max))
        self._lock = threading.Lock()
        self._submitted = 0
        self._completed = 0
        self._saturated = 0
        self._active = 0
        self._max_active = 0
        self._max_pending = 0
        self._closed = False

    def available(self) -> bool:
        with self._lock:
            return not self._closed

    def _invoke(self, operation: Callable[..., T], kwargs: dict[str, object]) -> T:
        with self._lock:
            self._active += 1
            self._max_active = max(self._max_active, self._active)
        try:
            return operation(**kwargs)
        finally:
            with self._lock:
                self._active = max(0, self._active - 1)

    async def run(self, operation: Callable[..., T], **kwargs: object) -> T:
        if not self.available():
            return await asyncio.to_thread(operation, **kwargs)
        if self._slots.locked():
            with self._lock:
                self._saturated += 1
        async with self._slots:
            with self._lock:
                self._submitted += 1
                pending = self._submitted - self._completed
                self._max_pending = max(self._max_pending, pending)
            try:
                loop = asyncio.get_running_loop()
                return await loop.run_in_executor(
                    self._executor,
                    partial(self._invoke, operation, dict(kwargs)),
                )
            finally:
                with self._lock:
                    self._completed += 1

    def diagnostics(self) -> dict[str, int]:
        with self._lock:
            return {
                "submitted": self._submitted,
                "completed": self._completed,
                "active": self._active,
                "maxActive": self._max_active,
                "maxPending": self._max_pending,
                "saturated": self._saturated,
            }

    def shutdown(self) -> None:
        with self._lock:
            if self._closed:
                return
            self._closed = True
        self._executor.shutdown(wait=False, cancel_futures=True)


async def run_realtime_control(
    request: Request,
    operation: Callable[..., T],
    **kwargs: object,
) -> T:
    executor = getattr(request.app.state, "realtime_control_executor", None)
    if isinstance(executor, RealtimeControlExecutor) and executor.available():
        return await executor.run(operation, **kwargs)
    return await asyncio.to_thread(operation, **kwargs)
