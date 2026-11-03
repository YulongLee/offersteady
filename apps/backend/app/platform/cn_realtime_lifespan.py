"""CN-only ownership for realtime I/O workers and scheduling observations."""
from __future__ import annotations

import asyncio
from contextlib import asynccontextmanager, suppress
from typing import Any, Callable

from app.platform.cn_realtime_loop_monitor import CnMainLoopMonitor
from app.services.cn_realtime_io_executor import CnRealtimeIoExecutor


def with_cn_realtime_lifespan(lifespan: Callable[..., Any], settings: Any):
    @asynccontextmanager
    async def managed(application):
        if settings.product_edition != "cn":
            async with lifespan(application):
                yield
            return

        # This outer context also closes our resources when the original
        # application's startup fails before reaching its own yield/finally.
        executor = CnRealtimeIoExecutor()
        monitor = CnMainLoopMonitor()
        application.state.cn_realtime_io_executor = executor
        application.state.cn_main_loop_monitor = monitor
        task = asyncio.create_task(monitor.run(), name="cn-main-loop-observation")
        try:
            async with lifespan(application):
                yield
        finally:
            task.cancel()
            with suppress(asyncio.CancelledError, Exception):
                await task
            executor.shutdown()

    return managed
