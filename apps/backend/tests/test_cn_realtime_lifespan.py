from __future__ import annotations

import asyncio
from contextlib import asynccontextmanager
from types import SimpleNamespace
from unittest.mock import patch

import pytest

from app.platform.cn_realtime_lifespan import with_cn_realtime_lifespan


class FakeExecutor:
    def __init__(self):
        self.shutdown_calls = 0

    def shutdown(self):
        self.shutdown_calls += 1


class FakeMonitor:
    def __init__(self):
        self.started = False
        self.finished = False

    async def run(self):
        self.started = True
        try:
            await asyncio.Event().wait()
        finally:
            self.finished = True


def test_cn_lifespan_owns_and_closes_workers_and_loop_probe():
    async def scenario():
        app = SimpleNamespace(state=SimpleNamespace())
        executor = FakeExecutor()
        monitor = FakeMonitor()
        events = []

        @asynccontextmanager
        async def base(_app):
            events.append("start")
            yield
            events.append("stop")

        with patch("app.platform.cn_realtime_lifespan.CnRealtimeIoExecutor", return_value=executor), patch(
            "app.platform.cn_realtime_lifespan.CnMainLoopMonitor", return_value=monitor
        ):
            async with with_cn_realtime_lifespan(base, SimpleNamespace(product_edition="cn"))(app):
                await asyncio.sleep(0)
                assert app.state.cn_realtime_io_executor is executor
                assert app.state.cn_main_loop_monitor is monitor
                assert monitor.started
                assert executor.shutdown_calls == 0
        assert events == ["start", "stop"]
        assert monitor.finished
        assert executor.shutdown_calls == 1

    asyncio.run(scenario())


def test_global_lifespan_does_not_create_cn_resources():
    async def scenario():
        app = SimpleNamespace(state=SimpleNamespace())

        @asynccontextmanager
        async def base(_app):
            yield

        with patch("app.platform.cn_realtime_lifespan.CnRealtimeIoExecutor", side_effect=AssertionError("CN worker")), patch(
            "app.platform.cn_realtime_lifespan.CnMainLoopMonitor", side_effect=AssertionError("CN observation")
        ):
            async with with_cn_realtime_lifespan(base, SimpleNamespace(product_edition="global"))(app):
                assert vars(app.state) == {}

    asyncio.run(scenario())


@pytest.mark.parametrize("phase", ["startup", "shutdown"])
def test_cn_resources_close_even_when_base_lifespan_fails(phase):
    async def scenario():
        app = SimpleNamespace(state=SimpleNamespace())
        executor = FakeExecutor()
        monitor = FakeMonitor()

        @asynccontextmanager
        async def base(_app):
            await asyncio.sleep(0)
            if phase == "startup":
                raise RuntimeError("synthetic-base-error")
            yield
            raise RuntimeError("synthetic-base-error")

        with patch("app.platform.cn_realtime_lifespan.CnRealtimeIoExecutor", return_value=executor), patch(
            "app.platform.cn_realtime_lifespan.CnMainLoopMonitor", return_value=monitor
        ):
            with pytest.raises(RuntimeError, match="synthetic-base-error"):
                async with with_cn_realtime_lifespan(base, SimpleNamespace(product_edition="cn"))(app):
                    pass
        assert executor.shutdown_calls == 1
        assert monitor.finished

    asyncio.run(scenario())


def test_broken_observer_does_not_change_success_or_skip_worker_shutdown():
    class BrokenMonitor(FakeMonitor):
        async def run(self):
            raise RuntimeError("synthetic-observer-failure")

    async def scenario():
        app = SimpleNamespace(state=SimpleNamespace())
        executor = FakeExecutor()

        @asynccontextmanager
        async def base(_app):
            yield

        with patch("app.platform.cn_realtime_lifespan.CnRealtimeIoExecutor", return_value=executor), patch(
            "app.platform.cn_realtime_lifespan.CnMainLoopMonitor", return_value=BrokenMonitor()
        ):
            async with with_cn_realtime_lifespan(base, SimpleNamespace(product_edition="cn"))(app):
                await asyncio.sleep(0)
        assert executor.shutdown_calls == 1

    asyncio.run(scenario())
