from __future__ import annotations

import logging
import threading
from time import monotonic, sleep

import pytest

from app.services.question_prefetch_scheduler import QuestionPrefetchScheduler


def submit(scheduler: QuestionPrefetchScheduler, revision: int, *, question_id: str = "question-a", **kwargs) -> bool:
    return scheduler.submit(user_id="synthetic-user", session_id="synthetic-session",
                            question_id=question_id, revision=revision,
                            question=f"synthetic question revision {revision}", **kwargs)


def wait_until(predicate, timeout: float = 2) -> None:
    deadline = monotonic() + timeout
    while not predicate():
        assert monotonic() < deadline
        sleep(0.002)


@pytest.fixture
def scheduler_factory():
    schedulers: list[QuestionPrefetchScheduler] = []

    def create(operation, **kwargs):
        scheduler = QuestionPrefetchScheduler(operation, logger=logging.getLogger("synthetic-prefetch"), **kwargs)
        schedulers.append(scheduler)
        return scheduler

    yield create
    for scheduler in schedulers:
        scheduler.shutdown(wait=True)
        assert scheduler.diagnostics()["workers"] == 0


def test_leading_starts_promptly_and_partial_burst_keeps_only_latest(scheduler_factory) -> None:
    started, release, latest_done = threading.Event(), threading.Event(), threading.Event()
    calls: list[int] = []
    published: list[int] = []

    def operation(*, revision, is_current, **_kwargs):
        calls.append(revision)
        if revision == 1:
            started.set()
            assert release.wait(2)
        if is_current():
            published.append(revision)
        if revision == 50:
            latest_done.set()

    scheduler = scheduler_factory(operation, quiet_seconds=0, max_wait_seconds=0)
    try:
        assert submit(scheduler, 1)
        assert started.wait(1)
        for revision in range(2, 51):
            assert submit(scheduler, revision)
        metrics = scheduler.diagnostics()
        assert metrics["active"] == 1
        assert metrics["pending"] == 1
        assert metrics["coalesced"] == 48
        release.set()
        assert latest_done.wait(1)
        assert calls == [1, 50]
        assert published == [50]
        assert scheduler.diagnostics()["maxActive"] == 1
    finally:
        release.set()


def test_final_uses_idle_second_worker_while_obsolete_partial_is_blocked(scheduler_factory) -> None:
    started, release, final_done = threading.Event(), threading.Event(), threading.Event()
    published: list[int] = []

    def operation(*, revision, is_current, **_kwargs):
        if revision == 1:
            started.set()
            assert release.wait(2)
        if is_current():
            published.append(revision)
        if revision == 2:
            final_done.set()

    scheduler = scheduler_factory(operation, quiet_seconds=10, max_wait_seconds=10)
    try:
        submit(scheduler, 1)
        assert started.wait(1)
        submit(scheduler, 2, is_final=True)
        assert final_done.wait(1)
        assert not release.is_set()
        assert published == [2]
        assert scheduler.diagnostics()["maxActive"] == 2
        release.set()
        wait_until(lambda: scheduler.diagnostics()["active"] == 0)
        assert published == [2]
    finally:
        release.set()


def test_global_worker_bound_and_final_priority_with_both_workers_busy(scheduler_factory) -> None:
    a_started, b_started, release_a, release_b, final_done = (threading.Event() for _ in range(5))
    calls: list[tuple[str, int]] = []

    def operation(*, question_id, revision, **_kwargs):
        calls.append((question_id, revision))
        if revision == 1:
            (a_started if question_id == "a" else b_started).set()
            assert (release_a if question_id == "a" else release_b).wait(2)
        if question_id == "a" and revision == 40:
            final_done.set()

    scheduler = scheduler_factory(operation, quiet_seconds=0, max_wait_seconds=0)
    try:
        submit(scheduler, 1, question_id="a")
        submit(scheduler, 1, question_id="b")
        assert a_started.wait(1) and b_started.wait(1)
        submit(scheduler, 2, question_id="c")
        for revision in range(2, 40):
            submit(scheduler, revision, question_id="a")
        submit(scheduler, 40, question_id="a", is_final=True)
        metrics = scheduler.diagnostics()
        assert metrics["active"] == 2 and metrics["pending"] == 2
        assert metrics["workers"] == 2
        release_a.set()
        assert final_done.wait(1)
        release_b.set()
        wait_until(lambda: scheduler.diagnostics()["active"] == scheduler.diagnostics()["pending"] == 0)
        assert calls[2] == ("a", 40)
        assert [revision for key, revision in calls if key == "a"] == [1, 40]
        assert scheduler.diagnostics()["maxActive"] == 2
    finally:
        release_a.set()
        release_b.set()


def test_same_revision_duplicate_and_final_hint_preserve_inflight_token(scheduler_factory) -> None:
    started, release = threading.Event(), threading.Event()
    guards = []
    calls: list[int] = []

    def operation(*, revision, is_current, **_kwargs):
        calls.append(revision)
        guards.append(is_current)
        started.set()
        assert release.wait(2)

    scheduler = scheduler_factory(operation)
    try:
        assert submit(scheduler, 1)
        assert started.wait(1)
        assert not submit(scheduler, 1)
        assert guards[0]()
        assert submit(scheduler, 1, is_final=True)
        assert guards[0]()
        assert not submit(scheduler, 2)
        assert not submit(scheduler, 0, is_final=True)
        release.set()
        wait_until(lambda: scheduler.diagnostics()["active"] == 0)
        assert calls == [1]
    finally:
        release.set()


def test_trailing_updates_observe_quiet_window(scheduler_factory) -> None:
    calls: list[int] = []
    trailing = threading.Event()

    def operation(*, revision, **_kwargs):
        calls.append(revision)
        if revision > 1:
            trailing.set()

    scheduler = scheduler_factory(operation, quiet_seconds=0.08, max_wait_seconds=0.5)
    submit(scheduler, 1)
    wait_until(lambda: scheduler.diagnostics()["completed"] == 1)
    submit(scheduler, 2)
    sleep(0.02)
    submit(scheduler, 3)
    assert not trailing.wait(0.03)
    assert trailing.wait(1)
    assert calls == [1, 3]


def test_continuous_updates_cannot_extend_maximum_wait(scheduler_factory) -> None:
    trailing = threading.Event()

    def operation(*, revision, **_kwargs):
        if revision > 1:
            trailing.set()

    scheduler = scheduler_factory(operation, quiet_seconds=0.5, max_wait_seconds=0.06)
    submit(scheduler, 1)
    wait_until(lambda: scheduler.diagnostics()["completed"] == 1)
    started_at = monotonic()
    revision = 2
    while not trailing.is_set() and monotonic() - started_at < 0.3:
        submit(scheduler, revision)
        revision += 1
        sleep(0.005)
    assert trailing.is_set()
    assert monotonic() - started_at < 0.3


def test_queue_age_and_key_budget_drop_optional_work_without_extra_workers(scheduler_factory) -> None:
    clock = [100.0]
    started, release, new_done = threading.Event(), threading.Event(), threading.Event()
    calls: list[str] = []

    def operation(*, question_id, **_kwargs):
        calls.append(question_id)
        if question_id == "a":
            started.set()
            assert release.wait(2)
        if question_id == "c":
            new_done.set()

    scheduler = scheduler_factory(operation, worker_count=1, max_keys=2, pending_ttl_seconds=10,
                                  state_ttl_seconds=20, clock=lambda: clock[0])
    try:
        submit(scheduler, 1, question_id="a")
        assert started.wait(1)
        assert submit(scheduler, 1, question_id="b")
        assert not submit(scheduler, 1, question_id="c")
        clock[0] += 11
        release.set()
        wait_until(lambda: scheduler.diagnostics()["active"] == 0)
        assert calls == ["a"]
        assert scheduler.diagnostics()["expired"] == 1
        assert submit(scheduler, 1, question_id="c")
        assert new_done.wait(1)
        assert scheduler.diagnostics()["maxKeys"] <= 2
        assert scheduler.diagnostics()["maxActive"] == 1
    finally:
        release.set()


def test_session_clear_revokes_tokens_and_does_not_cancel_other_sessions(scheduler_factory) -> None:
    started, release, other_done = threading.Event(), threading.Event(), threading.Event()
    guards = []
    calls: list[str] = []

    def operation(*, question_id, is_current, **_kwargs):
        calls.append(question_id)
        if question_id == "a":
            guards.append(is_current)
            started.set()
            assert release.wait(2)
        if question_id == "other":
            other_done.set()

    scheduler = scheduler_factory(operation, worker_count=1, quiet_seconds=0)
    try:
        submit(scheduler, 1, question_id="a")
        assert started.wait(1)
        submit(scheduler, 2, question_id="a")
        scheduler.submit(user_id="other-synthetic-user", session_id="other-session",
                         question_id="other", revision=1, question="other synthetic question")
        scheduler.clear_session(session_id="synthetic-session")
        assert not guards[0]()
        assert scheduler.diagnostics()["pending"] == 1
        release.set()
        assert other_done.wait(1)
        assert calls == ["a", "other"]
    finally:
        release.set()


def test_shutdown_revokes_work_and_callbacks_are_called_outside_lock(scheduler_factory) -> None:
    started, release = threading.Event(), threading.Event()
    guards = []
    scheduler = None

    def operation(*, is_current, **_kwargs):
        # A callback on another thread must acquire the scheduler lock while
        # retrieval is running, ruling out accidental lock-held execution.
        checked = threading.Event()
        thread = threading.Thread(target=lambda: (scheduler.diagnostics(), checked.set()))
        thread.start()
        assert checked.wait(1)
        thread.join()
        guards.append(is_current)
        started.set()
        assert release.wait(2)

    scheduler = scheduler_factory(operation, worker_count=1)
    try:
        submit(scheduler, 1)
        assert started.wait(1)
        submit(scheduler, 2)
        scheduler.shutdown()
        assert not guards[0]()
        assert not submit(scheduler, 3)
        assert scheduler.diagnostics()["pending"] == 0
        release.set()
        scheduler.shutdown(wait=True)
        assert scheduler.diagnostics()["workers"] == 0
        assert scheduler.diagnostics()["keys"] == 0
    finally:
        release.set()


def test_failed_optional_prefetch_does_not_stop_the_worker_or_log_text(scheduler_factory, caplog) -> None:
    done = threading.Event()

    def operation(*, revision, **_kwargs):
        if revision == 1:
            raise ValueError("synthetic private question must not be logged")
        done.set()

    caplog.set_level(logging.INFO)
    scheduler = scheduler_factory(operation, worker_count=1, quiet_seconds=0)
    submit(scheduler, 1)
    wait_until(lambda: scheduler.diagnostics()["completed"] == 1)
    submit(scheduler, 2)
    assert done.wait(1)
    assert scheduler.diagnostics()["failed"] == 1
    assert "synthetic private question" not in caplog.text
