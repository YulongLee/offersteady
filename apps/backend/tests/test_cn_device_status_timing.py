"""Synthetic-only timing and PostgreSQL context contracts; no external I/O."""
from __future__ import annotations

import asyncio
from concurrent.futures import ThreadPoolExecutor
from contextlib import contextmanager
import json
import logging
from math import isfinite
from threading import Barrier, Event
from types import SimpleNamespace
from unittest.mock import Mock

import pytest
from psycopg.rows import dict_row

from app.core.config import Settings
from app.core.logging import LOGGER_NAME, configure_logging
from app.platform import cn_device_status_timing as timing
from app.services.postgres_interview_session_repository import PostgresInterviewSessionRepository
from app.services.realtime_control_executor import RealtimeControlExecutor


def request(executor=None):
    return SimpleNamespace(app=SimpleNamespace(state=SimpleNamespace(realtime_control_executor=executor)))


def samples(caplog):
    return [json.loads(record.getMessage().split(" ", 1)[1]) for record in caplog.records
            if record.name == "offersteady.backend.cn_device_status_timing"]


@pytest.fixture(autouse=True)
def capture_private_logger(monkeypatch, caplog):
    timing._logger.addHandler(caplog.handler)
    monkeypatch.setattr(timing._logger, "propagate", False)
    try:
        yield
    finally:
        timing._logger.removeHandler(caplog.handler)


@pytest.fixture
def selected(monkeypatch, caplog):
    monkeypatch.setattr(timing, "_should_sample", lambda: True)
    caplog.set_level(logging.INFO, logger="offersteady.backend.cn_device_status_timing")


def test_sampling_has_constant_bounded_state_and_one_in_twenty(monkeypatch):
    monkeypatch.setattr(timing, "_sample_counter", 0)
    assert sum(timing._should_sample() for _ in range(2_000)) == 100
    assert timing._sample_counter == 0
    with ThreadPoolExecutor(max_workers=8) as executor:
        assert sum(executor.map(lambda _: timing._should_sample(), range(2_000))) == 100
    assert 0 <= timing._sample_counter < 20


def test_worker_installs_scope_and_separates_queue_work_and_phases(monkeypatch, caplog, selected):
    stamps = iter([1.0, 1.25, 1.25, 1.35, 1.45])
    monkeypatch.setattr(timing, "perf_counter", lambda: next(stamps))

    def operation(*, secret):
        assert timing._current_trace.get() is not None
        with timing.measure_device_status_phase("binding_repository"):
            assert secret == "synthetic-never-log-this"
        return {"same": secret}

    result = asyncio.run(timing.run_cn_device_status_control(request(), operation, secret="synthetic-never-log-this"))
    assert result == {"same": "synthetic-never-log-this"}
    [sample] = samples(caplog)
    assert sample["queue_ms"] == 250.0
    assert sample["work_ms"] == 200.0
    assert sample["binding_repository_ms"] == 100.0
    assert sample["binding_repository_count"] == 1
    assert sample["worker_failed"] == 0
    assert "synthetic-never-log-this" not in caplog.text
    assert set(sample) == {"schema", "sample_every", "queue_ms", "work_ms", "worker_failed"} | {
        f"{phase}_{suffix}" for phase in timing._PHASES for suffix in ("ms", "count")}
    assert all(type(value) in {int, float} and isfinite(value) and value >= 0 for value in sample.values())
    assert timing._current_trace.get() is None


def test_unselected_work_clears_inherited_context_and_does_not_time_or_log(monkeypatch, caplog):
    monkeypatch.setattr(timing, "_should_sample", lambda: False)
    clock = Mock(side_effect=AssertionError("unselected jobs must not clock"))
    monkeypatch.setattr(timing, "perf_counter", clock)
    trace = timing._Trace()
    token = timing._current_trace.set(trace)
    try:
        def operation():
            assert timing._current_trace.get() is None
            with timing.measure_device_status_phase("event_repository"):
                return 42
        assert asyncio.run(timing.run_cn_device_status_control(request(), operation)) == 42
        assert timing._current_trace.get() is trace
    finally:
        timing._current_trace.reset(token)
    clock.assert_not_called()
    assert samples(caplog) == [] and sum(trace.counts.values()) == 0


def test_phase_is_a_noop_without_scope_and_rejects_unbounded_labels(monkeypatch):
    clock = Mock()
    monkeypatch.setattr(timing, "perf_counter", clock)
    with timing.measure_device_status_phase("db_execute"):
        pass
    token = timing._current_trace.set(timing._Trace())
    try:
        with timing.measure_device_status_phase("synthetic-user-label-must-not-be-stored"):
            pass
        assert tuple(timing._current_trace.get().counts) == timing._PHASES
        assert sum(timing._current_trace.get().counts.values()) == 0
    finally:
        timing._current_trace.reset(token)
    clock.assert_not_called()


@pytest.mark.parametrize("bad_clock", [float("nan"), float("inf"), float("-inf"), "raises", "backward"])
def test_bad_clock_does_not_change_business_or_emit_nonfinite_values(monkeypatch, caplog, selected, bad_clock):
    if bad_clock == "raises":
        monkeypatch.setattr(timing, "perf_counter", Mock(side_effect=RuntimeError("synthetic-clock-secret")))
    elif bad_clock == "backward":
        counter = iter(range(100, 0, -1))
        monkeypatch.setattr(timing, "perf_counter", lambda: next(counter))
    else:
        monkeypatch.setattr(timing, "perf_counter", lambda: bad_clock)
    def operation():
        with timing.measure_device_status_phase("event_repository"):
            return "original-value"
    assert asyncio.run(timing.run_cn_device_status_control(request(), operation)) == "original-value"
    [sample] = samples(caplog)
    assert all(type(value) in {int, float} and isfinite(value) and value >= 0 for value in sample.values())
    assert sample["worker_failed"] == 0
    assert "synthetic-clock-secret" not in caplog.text


@pytest.mark.parametrize("observer", ["logger", "emit", "record", "trace"])
@pytest.mark.parametrize("business_fails", [False, True])
def test_observer_failures_preserve_result_and_original_exception(monkeypatch, selected, observer, business_fails):
    broken = Mock(side_effect=RuntimeError("synthetic-observer-secret"))
    if observer == "logger":
        monkeypatch.setattr(timing._logger, "info", broken)
    elif observer == "emit":
        monkeypatch.setattr(timing, "_emit", broken)
    elif observer == "record":
        monkeypatch.setattr(timing._Trace, "record", broken)
    else:
        monkeypatch.setattr(timing, "_Trace", broken)
    original = ValueError("synthetic-original-error")
    def operation():
        with timing.measure_device_status_phase("db_fetch"):
            if business_fails:
                raise original
            return 42
    if business_fails:
        with pytest.raises(ValueError) as error:
            asyncio.run(timing.run_cn_device_status_control(request(), operation))
        assert error.value is original
    else:
        assert asyncio.run(timing.run_cn_device_status_control(request(), operation)) == 42
    assert timing._current_trace.get() is None


def test_failed_trace_creation_still_isolates_inherited_fallback_context(monkeypatch, selected):
    outer = timing._Trace()
    token = timing._current_trace.set(outer)
    monkeypatch.setattr(timing, "_Trace", Mock(side_effect=RuntimeError("synthetic trace unavailable")))
    try:
        def operation():
            assert timing._current_trace.get() is None
            with timing.measure_device_status_phase("event_repository"):
                return 42
        assert asyncio.run(timing.run_cn_device_status_control(request(), operation)) == 42
        assert timing._current_trace.get() is outer
        assert sum(outer.counts.values()) == 0
    finally:
        timing._current_trace.reset(token)


def test_error_sample_contains_no_exception_or_arguments(caplog, selected):
    original = ValueError("synthetic-password=private")
    def operation(**kwargs):
        with timing.measure_device_status_phase("binding_repository"):
            raise original
    with pytest.raises(ValueError) as error:
        asyncio.run(timing.run_cn_device_status_control(request(), operation, session_id="synthetic-private-id"))
    assert error.value is original
    [sample] = samples(caplog)
    assert sample["worker_failed"] == 1 and sample["binding_repository_count"] == 1
    assert "synthetic-password" not in caplog.text and "synthetic-private-id" not in caplog.text


def test_parallel_workers_have_independent_samples_and_reused_worker_is_clean(monkeypatch, caplog, selected):
    async def scenario():
        executor = RealtimeControlExecutor(max_workers=2, queue_max=2)
        req = request(executor)
        both_running = Barrier(2)
        def first(*, phase):
            with timing.measure_device_status_phase(phase):
                both_running.wait(timeout=2)
                return phase
        try:
            results = await asyncio.gather(
                timing.run_cn_device_status_control(req, first, phase="binding_repository"),
                timing.run_cn_device_status_control(req, first, phase="event_repository"))
            assert set(results) == {"binding_repository", "event_repository"}
            # Query the same executor without the wrapper to verify final cleanup.
            assert await executor.run(lambda: timing._current_trace.get()) is None
            monkeypatch.setattr(timing, "_should_sample", lambda: False)
            assert await timing.run_cn_device_status_control(req, lambda: timing._current_trace.get()) is None
        finally:
            executor.shutdown()
    asyncio.run(scenario())
    records = samples(caplog)
    assert len(records) == 2
    assert sorted((s["binding_repository_count"], s["event_repository_count"]) for s in records) == [(0, 1), (1, 0)]


def test_cancellation_after_start_never_replays_and_worker_cleans_scope(caplog, selected):
    async def scenario():
        executor = RealtimeControlExecutor(max_workers=1, queue_max=1)
        started, finish = Event(), Event()
        calls = []
        def operation():
            calls.append(1)
            started.set()
            with timing.measure_device_status_phase("event_repository"):
                assert finish.wait(2)
            return 42
        try:
            task = asyncio.create_task(timing.run_cn_device_status_control(request(executor), operation))
            assert await asyncio.to_thread(started.wait, 2)
            task.cancel()
            with pytest.raises(asyncio.CancelledError):
                await task
            finish.set()
            assert await executor.run(lambda: timing._current_trace.get()) is None
            assert calls == [1]
        finally:
            finish.set()
            executor.shutdown()
    asyncio.run(scenario())
    [sample] = samples(caplog)
    assert sample["worker_failed"] == 0 and sample["event_repository_count"] == 1


def test_cancellation_while_waiting_for_slot_never_starts_job(caplog, selected):
    async def scenario():
        executor = RealtimeControlExecutor(max_workers=1, queue_max=1)
        started, finish = Event(), Event()
        def blocking():
            started.set()
            assert finish.wait(2)
        try:
            first = asyncio.create_task(executor.run(blocking))
            assert await asyncio.to_thread(started.wait, 2)
            queued = asyncio.create_task(executor.run(lambda: None))
            await asyncio.sleep(0)
            operation = Mock()
            waiting = asyncio.create_task(timing.run_cn_device_status_control(request(executor), operation))
            await asyncio.sleep(0)
            assert not waiting.done()
            waiting.cancel()
            with pytest.raises(asyncio.CancelledError):
                await waiting
            finish.set()
            await asyncio.gather(first, queued)
            operation.assert_not_called()
        finally:
            finish.set()
            executor.shutdown()
    asyncio.run(scenario())
    assert samples(caplog) == []


def projection_repository(monkeypatch, *, failure=None, missing=False):
    repository = object.__new__(PostgresInterviewSessionRepository)
    clock = [1.0]
    monkeypatch.setattr(timing, "perf_counter", lambda: clock[0])
    calls = []
    original = ValueError("synthetic-database-error")
    @contextmanager
    def cursor_context(*, row_factory):
        assert row_factory is dict_row
        clock[0] += .007
        calls.append("cursor-enter")
        try:
            yield SimpleNamespace(execute=execute, fetchone=fetchone)
        finally:
            clock[0] += .017
            calls.append("cursor-exit")
    def execute(query, parameters):
        calls.append((query, parameters))
        clock[0] += .011
        if failure == "execute":
            raise original
    def fetchone():
        calls.append("fetch")
        clock[0] += .013
        if failure == "fetch":
            raise original
        return None if missing else {"session_id": "synthetic-session", "owner_user_id": "synthetic-owner",
            "status": "live", "session_mode": None, "interview_audio_mode": ""}
    @contextmanager
    def connection_context():
        clock[0] += .003
        calls.append("connection-enter")
        try:
            yield SimpleNamespace(cursor=cursor_context)
        except BaseException as error:
            calls.append(("connection-error", error))
            raise
        finally:
            clock[0] += .019
            calls.append("connection-exit")
    def connect():
        calls.append("connect")
        clock[0] += .002
        if failure == "acquire":
            raise original
        return connection_context()
    monkeypatch.setattr(repository, "_connect", connect)
    return repository, calls, original


@pytest.mark.parametrize("missing", [False, True])
def test_projection_query_transaction_and_phase_boundaries(monkeypatch, missing):
    repository, calls, _ = projection_repository(monkeypatch, missing=missing)
    trace = timing._Trace()
    token = timing._current_trace.set(trace)
    try:
        state = repository.get_control_state("synthetic-session")
    finally:
        timing._current_trace.reset(token)
    assert state is None if missing else (state.session_mode == "interview" and state.interview_audio_mode == "computer")
    assert calls == ["connect", "connection-enter", "cursor-enter",
        ("""SELECT session_id, owner_user_id, status, session_mode, interview_audio_mode
                   FROM interview_sessions WHERE session_id = %s AND deleted_at_ms IS NULL""", ("synthetic-session",)),
        "fetch", "cursor-exit", "connection-exit"]
    assert trace.counts == {"db_acquire": 1, "db_execute": 1, "db_fetch": 1, "binding_repository": 0, "event_repository": 0}
    assert trace.totals["db_acquire"] == pytest.approx(5)
    assert trace.totals["db_execute"] == pytest.approx(11)
    assert trace.totals["db_fetch"] == pytest.approx(13)


@pytest.mark.parametrize("failure", ["acquire", "execute", "fetch"])
def test_projection_failure_is_not_replayed_and_context_gets_original_exception(monkeypatch, failure):
    repository, calls, original = projection_repository(monkeypatch, failure=failure)
    trace = timing._Trace()
    token = timing._current_trace.set(trace)
    try:
        with pytest.raises(ValueError) as error:
            repository.get_control_state("synthetic-session")
        assert error.value is original
    finally:
        timing._current_trace.reset(token)
    assert calls.count("connect") == 1
    if failure != "acquire":
        assert ("connection-error", original) in calls
        assert calls[-2:] == [("connection-error", original), "connection-exit"]
    assert trace.counts["db_acquire"] == 1
    assert trace.counts["db_execute"] == (failure != "acquire")
    assert trace.counts["db_fetch"] == (failure == "fetch")


def test_production_configured_logger_receives_info_without_child_level_override(monkeypatch, capsys):
    parent = logging.getLogger(LOGGER_NAME)
    monkeypatch.setattr(parent, "handlers", [])
    monkeypatch.setattr(parent, "level", parent.level)
    monkeypatch.setattr(parent, "propagate", parent.propagate)
    monkeypatch.setattr(timing._logger, "level", logging.NOTSET)
    monkeypatch.setattr(timing._logger, "propagate", True)
    configure_logging(Settings(_env_file=None, log_level="INFO"))
    assert timing._logger.isEnabledFor(logging.INFO)
    timing._emit(timing._Trace(), queue_ms=1, work_ms=2, worker_failed=0)
    emitted = capsys.readouterr().err
    assert emitted.startswith("cn_device_status_timing ")
    assert json.loads(emitted.split(" ", 1)[1])["queue_ms"] == 1
