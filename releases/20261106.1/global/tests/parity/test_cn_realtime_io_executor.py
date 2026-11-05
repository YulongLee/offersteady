"""Synthetic scheduling/ownership regressions. No provider, DB or application startup."""
from __future__ import annotations

import asyncio
import json
import threading
from types import SimpleNamespace

import pytest

from app.services import cn_realtime_io_executor as module
from app.services.cn_realtime_io_executor import CnRealtimeIoExecutor, run_cn_realtime_io
from app.services.realtime_control_executor import RealtimeControlExecutor


async def started(event):
    assert await asyncio.wait_for(asyncio.to_thread(event.wait, 1), 2)


def test_defaults_and_shutdown_are_bounded():
    executor = CnRealtimeIoExecutor()
    values = executor.diagnostics()
    assert values["ingress"]["configuredWorkers"] == 4
    assert values["ingress"]["configuredQueueMax"] == 16
    assert values["lifecycle"]["configuredWorkers"] == 2
    assert values["lifecycle"]["configuredQueueMax"] == 8
    executor.shutdown()
    executor.shutdown()
    assert all(executor.diagnostics()[name]["closed"] == 1 for name in ("ingress", "lifecycle"))


def test_slow_lifecycle_does_not_occupy_ingress_control_or_loop():
    async def scenario():
        executor = CnRealtimeIoExecutor(lifecycle_workers=1, lifecycle_queue_max=0)
        control = RealtimeControlExecutor(max_workers=1, queue_max=1)
        entered, release = threading.Event(), threading.Event()
        def close():
            entered.set()
            assert release.wait(2)
        task = asyncio.create_task(executor.run(close, lane="lifecycle", operation_name="publisher_disconnect"))
        try:
            await started(entered)
            assert await asyncio.wait_for(executor.run(lambda: 17, operation_name="ingest_frame"), .5) == 17
            assert await asyncio.wait_for(control.run(lambda: 19), .5) == 19
            await asyncio.sleep(0)
            assert not task.done()
        finally:
            release.set()
            await task
            executor.shutdown()
            control.shutdown()
    asyncio.run(scenario())


def test_cancel_running_job_drains_once_without_releasing_capacity_early():
    async def scenario():
        executor = CnRealtimeIoExecutor(ingress_workers=1, ingress_queue_max=0)
        entered, release = threading.Event(), threading.Event()
        calls = []
        def operation():
            calls.append("run")
            entered.set()
            assert release.wait(2)
            return 11
        first = asyncio.create_task(executor.run(operation, operation_name="ingest_frame"))
        try:
            await started(entered)
            first.cancel("synthetic-original-cancellation")
            await asyncio.sleep(.01)
            first.cancel()
            second = asyncio.create_task(executor.run(lambda: calls.append("second"), operation_name="ingest_frame"))
            await asyncio.sleep(.01)
            assert not first.done() and not second.done()
            assert executor.diagnostics()["ingress"]["pending"] == 1
            assert executor.diagnostics()["ingress"]["submitted"] == 1
            second.cancel()
            with pytest.raises(asyncio.CancelledError):
                await second
            release.set()
            with pytest.raises(asyncio.CancelledError) as cancelled:
                await first
            assert cancelled.value.args == ("synthetic-original-cancellation",)
            assert calls == ["run"]
            assert executor.diagnostics()["ingress"]["completed"] == 1
            assert await executor.run(lambda: 23, operation_name="ingest_frame") == 23
        finally:
            release.set()
            executor.shutdown()
    asyncio.run(scenario())


@pytest.mark.parametrize("configured", [False, True])
def test_cancel_created_resource_compensates_once_and_drains_cleanup(configured):
    async def scenario():
        executor = CnRealtimeIoExecutor() if configured else None
        surface = SimpleNamespace(app=SimpleNamespace(state=SimpleNamespace()))
        if executor:
            surface.app.state.cn_realtime_io_executor = executor
        entered, release = threading.Event(), threading.Event()
        cleanup_entered, cleanup_release = threading.Event(), threading.Event()
        calls = []
        def create():
            calls.append("create")
            entered.set()
            assert release.wait(2)
            return "synthetic-resource"
        def cleanup(result):
            calls.append(("cleanup", result))
            cleanup_entered.set()
            assert cleanup_release.wait(2)
        task = asyncio.create_task(run_cn_realtime_io(surface, create, lane="lifecycle",
            operation_name="publisher_create", on_abandoned_result=cleanup))
        try:
            await started(entered)
            task.cancel()
            task.cancel()
            release.set()
            await started(cleanup_entered)
            task.cancel()
            await asyncio.sleep(.01)
            assert not task.done()
            cleanup_release.set()
            with pytest.raises(asyncio.CancelledError):
                await task
            assert calls == ["create", ("cleanup", "synthetic-resource")]
        finally:
            release.set()
            cleanup_release.set()
            if executor:
                executor.shutdown()
    asyncio.run(scenario())


def test_second_cancel_while_compensation_waits_for_lane_cannot_skip_cleanup():
    async def scenario():
        executor = CnRealtimeIoExecutor(lifecycle_workers=1, lifecycle_queue_max=0)
        entered, release = threading.Event(), threading.Event()
        occupied, release_occupied = threading.Event(), threading.Event()
        calls = []
        def create():
            entered.set()
            assert release.wait(2)
            return "created"
        def occupy():
            occupied.set()
            assert release_occupied.wait(2)
        task = asyncio.create_task(executor.run(create, operation_name="publisher_connect",
            on_abandoned_result=lambda result: calls.append(result)))
        blocker = asyncio.create_task(executor.run(occupy, lane="lifecycle", operation_name="publisher_disconnect"))
        try:
            await started(entered)
            await started(occupied)
            task.cancel()
            release.set()
            await asyncio.sleep(.01)
            task.cancel()
            await asyncio.sleep(.01)
            assert calls == [] and not task.done()
            release_occupied.set()
            await blocker
            with pytest.raises(asyncio.CancelledError):
                await task
            assert calls == ["created"]
        finally:
            release.set()
            release_occupied.set()
            executor.shutdown()
    asyncio.run(scenario())


def test_error_propagates_without_replay_or_compensation():
    async def scenario():
        executor = CnRealtimeIoExecutor()
        calls = []
        error = ValueError("synthetic-private-error")
        def fail():
            calls.append(1)
            raise error
        try:
            with pytest.raises(ValueError) as caught:
                await executor.run(fail, operation_name="ingest_frame", on_abandoned_result=lambda result: calls.append(2))
            assert caught.value is error and calls == [1]
        finally:
            executor.shutdown()
    asyncio.run(scenario())


def test_shutdown_wakes_waiters_cancels_queued_and_keeps_loop_responsive():
    async def scenario():
        executor = CnRealtimeIoExecutor(ingress_workers=1, ingress_queue_max=1)
        entered, release = threading.Event(), threading.Event()
        calls = []
        def busy():
            entered.set()
            assert release.wait(2)
        first = asyncio.create_task(executor.run(busy, operation_name="ingest_frame"))
        try:
            await started(entered)
            queued = asyncio.create_task(executor.run(lambda: calls.append("queued"), operation_name="ingest_frame"))
            await asyncio.sleep(.01)
            waiter = asyncio.create_task(executor.run(lambda: calls.append("waiting"), operation_name="ingest_frame"))
            await asyncio.sleep(.01)
            executor.shutdown()
            with pytest.raises(asyncio.CancelledError):
                await queued
            with pytest.raises(RuntimeError, match="closed"):
                await waiter
            assert calls == [] and not first.done()
            release.set()
            await first
            assert executor.diagnostics()["ingress"]["pending"] == 0
        finally:
            release.set()
            executor.shutdown()
    asyncio.run(scenario())


def test_work_timing_is_fixed_numeric_private_and_observer_failure_safe(monkeypatch, caplog):
    async def scenario():
        executor = CnRealtimeIoExecutor()
        try:
            assert await executor.run(lambda **kwargs: 31, operation_name="ingest_frame", secret="synthetic-private-secret") == 31
            with pytest.raises(ValueError):
                await executor.run(lambda: None, operation_name="synthetic-user-id")
        finally:
            executor.shutdown()
    monkeypatch.setattr(module, "_should_sample", lambda: True)
    with caplog.at_level("INFO", logger=module._logger.name):
        asyncio.run(scenario())
    samples = [json.loads(r.getMessage().split(" ", 1)[1]) for r in caplog.records if r.getMessage().startswith("cn_realtime_io_timing ")]
    assert samples and all(v["lane"] == "ingress" and v["operation"] == "ingest_frame" for v in samples)
    assert all(type(v[k]) in (float, int) and v[k] >= 0 for v in samples for k in ("queue_ms", "work_ms", "resume_ms"))
    assert "synthetic-private-secret" not in caplog.text
    monkeypatch.setattr(module._logger, "info", lambda *a, **k: (_ for _ in ()).throw(RuntimeError("logging failed")))
    asyncio.run(scenario())
    monkeypatch.setattr(module, "perf_counter", lambda: (_ for _ in ()).throw(RuntimeError("clock failed")))
    asyncio.run(scenario())


@pytest.mark.parametrize("lane", ["ingress", "lifecycle"])
def test_cancel_and_shutdown_retains_bounded_late_resource_compensation(lane):
    async def scenario():
        executor = CnRealtimeIoExecutor(ingress_workers=1, ingress_queue_max=0,
                                       lifecycle_workers=1, lifecycle_queue_max=0)
        entered, release = threading.Event(), threading.Event()
        calls = []
        def create():
            entered.set()
            assert release.wait(2)
            return "created"
        task = asyncio.create_task(executor.run(create, lane=lane, operation_name="publisher_create",
            on_abandoned_result=lambda value: calls.append(value)))
        try:
            await started(entered)
            task.cancel()
            await asyncio.sleep(0)
            executor.shutdown()
            with pytest.raises(RuntimeError, match="closed"):
                await executor.run(lambda: calls.append("forbidden"), operation_name="ingest_frame")
            assert executor.diagnostics()["poolsClosed"] == 0
            release.set()
            with pytest.raises(asyncio.CancelledError):
                await task
            assert calls == ["created"]
            assert executor.diagnostics()["cleanupFailed"] == 0
            assert executor.diagnostics()["poolsClosed"] == 1
        finally:
            release.set()
            executor.shutdown()
    asyncio.run(scenario())


def test_worker_cancelled_error_is_not_mistaken_for_repeated_caller_cancellation():
    async def scenario():
        executor = CnRealtimeIoExecutor()
        calls = []
        def operation():
            calls.append(1)
            raise asyncio.CancelledError("synthetic worker cancellation")
        try:
            with pytest.raises(asyncio.CancelledError):
                await asyncio.wait_for(executor.run(operation, operation_name="ingest_frame"), .5)
            assert calls == [1]
        finally:
            executor.shutdown()
    asyncio.run(scenario())


def test_compensation_failure_is_counted_even_when_not_sampled(monkeypatch, caplog):
    async def scenario():
        executor = CnRealtimeIoExecutor()
        entered, release = threading.Event(), threading.Event()
        def create():
            entered.set()
            assert release.wait(2)
            return "created"
        def fail_cleanup(value):
            raise ValueError("synthetic-private-cleanup-error")
        task = asyncio.create_task(executor.run(create, operation_name="publisher_create", on_abandoned_result=fail_cleanup))
        try:
            await started(entered)
            task.cancel()
            release.set()
            with pytest.raises(asyncio.CancelledError):
                await task
            assert executor.diagnostics()["cleanupFailed"] == 1
        finally:
            release.set()
            executor.shutdown()
    monkeypatch.setattr(module, "_should_sample", lambda: False)
    with caplog.at_level("WARNING", logger=module._logger.name):
        asyncio.run(scenario())
    assert 'cn_realtime_io_cleanup_failed {"count":1}' in caplog.text
    assert "synthetic-private-cleanup-error" not in caplog.text


def test_shutdown_preserves_already_queued_compensation_and_its_original_bound():
    async def scenario():
        executor = CnRealtimeIoExecutor(lifecycle_workers=1, lifecycle_queue_max=1)
        started_create, release_create = threading.Event(), threading.Event()
        started_close, release_close = threading.Event(), threading.Event()
        calls = []
        def create():
            started_create.set()
            assert release_create.wait(2)
            return "owned"
        def close():
            started_close.set()
            assert release_close.wait(2)
        blocker = asyncio.create_task(executor.run(close, lane="lifecycle", operation_name="publisher_disconnect"))
        task = asyncio.create_task(executor.run(create, operation_name="publisher_connect",
            on_abandoned_result=lambda result: calls.append(result)))
        try:
            await started(started_create)
            await started(started_close)
            task.cancel()
            release_create.set()
            for _ in range(100):
                if executor.diagnostics()["lifecycle"]["pending"] == 2:
                    break
                await asyncio.sleep(.001)
            assert executor.diagnostics()["lifecycle"]["pending"] == 2
            executor.shutdown()
            await asyncio.sleep(0)
            assert not task.done() and calls == []
            release_close.set()
            await blocker
            with pytest.raises(asyncio.CancelledError):
                await task
            assert calls == ["owned"]
            assert executor.diagnostics()["lifecycle"]["maxPending"] == 2
            assert executor.diagnostics()["poolsClosed"] == 1
        finally:
            release_create.set()
            release_close.set()
            executor.shutdown()
    asyncio.run(scenario())


def test_shutdown_then_cancel_admission_waiters_cannot_expand_compensation_capacity():
    async def scenario():
        executor = CnRealtimeIoExecutor(lifecycle_workers=1, lifecycle_queue_max=0)
        close_started, close_release = threading.Event(), threading.Event()
        create_started = [threading.Event() for _ in range(3)]
        create_release = threading.Event()
        cleaned = []
        def busy_close():
            close_started.set()
            assert close_release.wait(2)
        def create(index):
            create_started[index].set()
            assert create_release.wait(2)
            return index
        blocker = asyncio.create_task(executor.run(busy_close, lane="lifecycle", operation_name="publisher_disconnect"))
        waiters, owners = [], []
        try:
            await started(close_started)
            waiters = [asyncio.create_task(executor.run(lambda: None, lane="lifecycle", operation_name="publisher_create")) for _ in range(3)]
            owners = [asyncio.create_task(executor.run(create, index=index, operation_name="publisher_connect",
                on_abandoned_result=lambda value: cleaned.append(value))) for index in range(3)]
            for event in create_started:
                await started(event)
            for owner in owners:
                owner.cancel()
            await asyncio.sleep(0)
            executor.shutdown()
            for waiter in waiters:
                waiter.cancel()
            await asyncio.gather(*waiters, return_exceptions=True)
            create_release.set()
            for _ in range(100):
                if executor.diagnostics()["lifecycle"]["waiting"] >= 3:
                    break
                await asyncio.sleep(.001)
            assert executor.diagnostics()["lifecycle"]["pending"] == 1
            assert executor.diagnostics()["lifecycle"]["maxPending"] == 1
            assert cleaned == []
            close_release.set()
            await blocker
            results = await asyncio.gather(*owners, return_exceptions=True)
            assert all(isinstance(value, asyncio.CancelledError) for value in results)
            assert sorted(cleaned) == [0, 1, 2]
            assert executor.diagnostics()["lifecycle"]["maxPending"] == 1
            assert executor.diagnostics()["poolsClosed"] == 1
        finally:
            close_release.set()
            create_release.set()
            executor.shutdown()
    asyncio.run(scenario())
