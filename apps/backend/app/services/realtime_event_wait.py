from __future__ import annotations

import asyncio
from concurrent.futures import ThreadPoolExecutor
from functools import partial
import threading
from typing import Callable, TypeVar

from fastapi import Request


T = TypeVar("T")


class RealtimeEventWaitExecutor:
    """Keep blocking Redis event waits away from the shared asyncio executor."""

    def __init__(self, *, max_workers: int, thread_name_prefix: str = "realtime-event-wait") -> None:
        self._max_workers = max(1, max_workers)
        self._executor = ThreadPoolExecutor(
            max_workers=self._max_workers,
            thread_name_prefix=thread_name_prefix,
        )
        self._lock = threading.Lock()
        self._submitted = 0
        self._completed = 0
        self._active = 0
        self._max_active = 0
        self._closed = False

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
        with self._lock:
            self._submitted += 1
        loop = asyncio.get_running_loop()
        try:
            return await loop.run_in_executor(self._executor, partial(self._invoke, operation, dict(kwargs)))
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
                "pending": max(0, self._submitted - self._completed - self._active),
                "configuredWorkers": self._max_workers,
            }

    def shutdown(self) -> None:
        with self._lock:
            if self._closed:
                return
            self._closed = True
        self._executor.shutdown(wait=False, cancel_futures=True)


async def run_realtime_event_wait(
    request: Request,
    operation: Callable[..., T],
    **kwargs: object,
) -> T:
    executor = getattr(request.app.state, "realtime_event_wait_executor", None)
    if isinstance(executor, RealtimeEventWaitExecutor):
        return await executor.run(operation, **kwargs)
    return await asyncio.to_thread(operation, **kwargs)


async def run_screenshot_event_wait(
    request: Request,
    operation: Callable[..., T],
    **kwargs: object,
) -> T:
    executor = getattr(request.app.state, "screenshot_event_wait_executor", None)
    if isinstance(executor, RealtimeEventWaitExecutor):
        return await executor.run(operation, **kwargs)
    return await asyncio.to_thread(operation, **kwargs)
