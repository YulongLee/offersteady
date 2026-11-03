from __future__ import annotations

import asyncio
import json
from unittest.mock import patch

from app.platform.cn_realtime_loop_monitor import CnMainLoopMonitor


def test_loop_observations_are_bounded_numeric_and_do_not_store_content():
    monitor = CnMainLoopMonitor(max_samples=3, emit_every=100)
    for value in [1.0, 2.0, 50.0, 250.0, 900.0]:
        monitor.observe(value)
    before = monitor.summary()
    for value in [float("nan"), float("inf"), -1.0, "private-content"]:
        monitor.observe(value)  # type: ignore[arg-type]
    assert monitor.summary() == before
    assert before == {
        "sampleCount": 3, "observations": 5, "capacity": 3, "intervalMs": 250.0,
        "p50Ms": 250.0, "p95Ms": 900.0, "maxMs": 900.0,
        "over50Ms": 3, "over250Ms": 2,
    }


def test_loop_timer_distinguishes_delayed_scheduling_and_resets_after_pause():
    async def scenario():
        now = 0.0
        sleeps = 0

        async def tick(interval):
            nonlocal now, sleeps
            sleeps += 1
            if sleeps == 4:
                raise asyncio.CancelledError
            now += interval + (0.8 if sleeps == 2 else 0)

        monitor = CnMainLoopMonitor(clock=lambda: now, sleep=tick, emit_every=100)
        try:
            await monitor.run()
        except asyncio.CancelledError:
            pass
        summary = monitor.summary()
        assert summary["sampleCount"] == 3
        assert summary["maxMs"] == 800.0
        assert summary["over250Ms"] == 1
        assert summary["p50Ms"] == 0.0

    asyncio.run(scenario())


def test_broken_clock_and_logger_do_not_terminate_probe_or_leak_data():
    async def scenario():
        reads = 0
        sleeps = 0

        def clock():
            nonlocal reads
            reads += 1
            if reads == 2:
                raise RuntimeError("private-source-error")
            if reads == 4:
                return float("nan")
            return float(reads)

        async def tick(_interval):
            nonlocal sleeps
            sleeps += 1
            if sleeps == 6:
                raise asyncio.CancelledError

        monitor = CnMainLoopMonitor(clock=clock, sleep=tick, emit_every=1)
        with patch("app.platform.cn_realtime_loop_monitor._logger.info", side_effect=RuntimeError("private-log-error")):
            try:
                await monitor.run()
            except asyncio.CancelledError:
                pass
        assert sleeps == 6
        assert monitor.summary()["observations"] == 1

    asyncio.run(scenario())


def test_logged_summary_has_only_fixed_numeric_fields():
    monitor = CnMainLoopMonitor(emit_every=1)
    with patch("app.platform.cn_realtime_loop_monitor._logger.info") as emit:
        monitor.observe(4.5)
    emit.assert_called_once()
    message, payload = emit.call_args.args
    assert message == "cn_main_loop_timing %s"
    record = json.loads(payload)
    assert record["schema"] == 1
    assert all(type(value) in (int, float) for value in record.values())
    assert not any(word in payload for word in ["session", "user", "device", "private", "http"])
