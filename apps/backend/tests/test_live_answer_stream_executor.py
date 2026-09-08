from __future__ import annotations

import asyncio
import threading

from app.services.live_answer_stream_executor import LiveAnswerStreamExecutor


def test_stream_preserves_order_and_releases_capacity() -> None:
    async def scenario() -> None:
        executor = LiveAnswerStreamExecutor(max_workers=1, queue_max=0, event_queue_max=1)
        lease = executor.try_acquire()
        assert lease is not None

        def producer():
            yield "one"
            yield "two"
            yield "three"

        assert [frame async for frame in executor.stream(lease, producer)] == ["one", "two", "three"]
        for _ in range(100):
            if executor.diagnostics()["completed"] == 1:
                break
            await asyncio.sleep(0.001)
        assert executor.diagnostics()["completed"] == 1
        next_lease = executor.try_acquire()
        assert next_lease is not None
        next_lease.release()
        executor.shutdown()

    asyncio.run(scenario())


def test_stream_rejects_saturation_without_starting_extra_producer() -> None:
    executor = LiveAnswerStreamExecutor(max_workers=1, queue_max=0, event_queue_max=1)
    lease = executor.try_acquire()
    assert lease is not None
    assert executor.try_acquire() is None
    assert executor.diagnostics()["saturated"] == 1
    lease.release()
    next_lease = executor.try_acquire()
    assert next_lease is not None
    next_lease.release()
    executor.shutdown()


def test_stream_propagates_error_and_releases_capacity() -> None:
    async def scenario() -> None:
        executor = LiveAnswerStreamExecutor(max_workers=1, queue_max=0, event_queue_max=1)
        lease = executor.try_acquire()
        assert lease is not None

        def producer():
            yield "before-error"
            raise RuntimeError("synthetic-stream-error")

        received: list[str] = []
        try:
            async for frame in executor.stream(lease, producer):
                received.append(frame)
        except RuntimeError as exc:
            assert str(exc) == "synthetic-stream-error"
        else:
            raise AssertionError("producer error was not propagated")
        assert received == ["before-error"]
        for _ in range(100):
            if executor.diagnostics()["completed"] == 1:
                break
            await asyncio.sleep(0.001)
        assert executor.diagnostics()["completed"] == 1
        executor.shutdown()

    asyncio.run(scenario())


def test_stream_cancellation_stops_delivery_and_releases_capacity() -> None:
    async def scenario() -> None:
        executor = LiveAnswerStreamExecutor(max_workers=1, queue_max=0, event_queue_max=1)
        lease = executor.try_acquire()
        assert lease is not None
        producer_stopped = threading.Event()

        def producer():
            try:
                sequence = 0
                while True:
                    sequence += 1
                    yield str(sequence)
            finally:
                producer_stopped.set()

        stream = executor.stream(lease, producer)
        assert await anext(stream) == "1"
        await stream.aclose()
        assert await asyncio.to_thread(producer_stopped.wait, 1.0)
        assert executor.diagnostics()["completed"] == 1
        executor.shutdown()

    asyncio.run(scenario())
