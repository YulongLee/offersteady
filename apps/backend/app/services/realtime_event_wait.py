from __future__ import annotations

import asyncio
from concurrent.futures import ThreadPoolExecutor
from functools import partial
from typing import Callable, TypeVar

from fastapi import Request


T = TypeVar("T")


class RealtimeEventWaitExecutor:
    """Keep blocking Redis event waits away from the shared asyncio executor."""

    def __init__(self, *, max_workers: int) -> None:
        self._executor = ThreadPoolExecutor(
            max_workers=max(1, max_workers),
            thread_name_prefix="realtime-event-wait",
        )

    async def run(self, operation: Callable[..., T], **kwargs: object) -> T:
        loop = asyncio.get_running_loop()
        return await loop.run_in_executor(self._executor, partial(operation, **kwargs))

    def shutdown(self) -> None:
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
