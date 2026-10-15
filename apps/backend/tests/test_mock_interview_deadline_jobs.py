"""Synthetic job-contract races; no database, credentials or real user content."""
from __future__ import annotations

import asyncio
import copy
import json
import logging
from dataclasses import asdict
from datetime import datetime
from threading import RLock
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock
from zoneinfo import ZoneInfo

import pytest

from app.core.config import Settings
from app.core.errors import DomainRequestError
from app.core.logging import LOGGER_NAME
from app.schemas.mock_interview import MockQuestion, MockReport
from app.services.mock_interview_generation import MockGenerationUnavailable, MockInterviewGenerator
from app.services.mock_interview_jobs import MockInterviewJobs
from app.services.mock_interview_repository import round_state
from app.services.mock_interview_rounds import MockRoundState


OWNER = "synthetic-deadline-owner"
SESSION = "synthetic-deadline-session"
PRIVATE = "SYNTHETIC_DEADLINE_PRIVATE_RESUME"
# The fixed deadline crosses CN midnight; the daily billing date cannot reset it.
START = int(datetime(2026, 10, 15, 23, 30, tzinfo=ZoneInfo("Asia/Shanghai")).timestamp() * 1000)
DEADLINE = START + 60 * 60 * 1000


class Clock:
    def __init__(self, now_ms=START):
        self.value = now_ms

    def __call__(self):
        return self.value


class JobRepository:
    """Small durable-claim contract double, including stale operation rejection."""
    def __init__(self, clock, *, deadline=DEADLINE, answered=False, report=False, edition="cn"):
        self.clock = clock
        self.deadline = deadline
        self.settings = Settings(_env_file=None, product_edition=edition,
                                 chat_qwen_api_key="", mock_interview_provider_timeout_seconds=1)
        state = MockRoundState().start()
        if answered:
            state = state.publish_question(state.operation_id, "合成问题：如何验证幂等？")
            state = state.listen(state.rounds[-1].question_id, START)
            state = state.submit(question_id=state.rounds[-1].question_id,
                                 answer="合成回答：用唯一键验证。", submission_id="synthetic-answer")
        if report:
            state = state.end()
        self.record = {"session_id": SESSION, "owner_user_id": OWNER, "data": {
            "state": asdict(state), "generation_claim": None, "generation_claim_until_ms": 0,
            "resume_id": "synthetic-resume", "resume_version": "synthetic-version",
            "target_role": "合成开发岗位", "started_at_ms": START, "deadline_at_ms": deadline,
            "provider_failures": 0, "end_reason": None}}
        self.lock = RLock()
        self.claims = []
        self.finishes = []
        self.expiries = []
        self.after_get = None
        self.before_claim = None
        self.before_finish = None

    def get(self, *, user_id, session_id):
        assert (user_id, session_id) == (OWNER, SESSION)
        with self.lock:
            result = copy.deepcopy(self.record)
            hook, self.after_get = self.after_get, None
            if hook:
                hook()
            return result

    def duration_deadline(self, record):
        return self.deadline

    def _expire(self, now_ms):
        state = round_state(self.record)
        if self.deadline is None or now_ms < self.deadline or state.phase in ("generating_report", "completed"):
            return False
        self.record["data"].update(state=asdict(state.end()), end_reason="time_limit",
                                   generation_claim=None, generation_claim_until_ms=0)
        return True

    def expire_duration(self, *, user_id, session_id, now_ms):
        assert (user_id, session_id) == (OWNER, SESSION)
        with self.lock:
            self.expiries.append(now_ms)
            self._expire(now_ms)
            return copy.deepcopy(self.record)

    def claim_generation(self, *, user_id, session_id, operation_id, now_ms):
        assert (user_id, session_id) == (OWNER, SESSION)
        with self.lock:
            hook, self.before_claim = self.before_claim, None
            if hook:
                hook()
            self.claims.append((operation_id, now_ms))
            if self._expire(now_ms):
                return copy.deepcopy(self.record)
            state = round_state(self.record)
            if state.operation_id != operation_id or state.phase not in ("generating_question", "generating_report"):
                raise DomainRequestError("mock-interview", "generate", "合成过期操作", 409, "mock_stale_operation")
            if self.record["data"].get("generation_claim"):
                raise DomainRequestError("mock-interview", "generate", "合成生成占用", 409, "mock_generation_in_progress")
            self.record["data"].update(generation_claim=f"synthetic-claim-{len(self.claims)}",
                                       generation_claim_until_ms=now_ms + 16_000)
            return copy.deepcopy(self.record)

    def finish_generation(self, **values):
        assert (values["user_id"], values["session_id"]) == (OWNER, SESSION)
        with self.lock:
            hook, self.before_finish = self.before_finish, None
            if hook:
                hook()
            self.finishes.append(dict(values))
            if self._expire(values["now_ms"]):
                return copy.deepcopy(self.record)
            data, state = self.record["data"], round_state(self.record)
            if state.operation_id != values["operation_id"] or data["generation_claim"] != values["claim_id"]:
                raise DomainRequestError("mock-interview", "generate", "合成结果已过期", 409, "mock_stale_operation")
            if values.get("failed"):
                data["provider_failures"] += int(values.get("provider_fault", False))
                data["error"] = "generation_unavailable"
            elif "question" in values:
                data["state"] = asdict(state.publish_question(values["operation_id"], values["question"]))
            else:
                data.update(state=asdict(state.complete(values["operation_id"])), report=values["report"])
            data.update(generation_claim=None, generation_claim_until_ms=0)
            return copy.deepcopy(self.record)


def harness(*, clock=None, generator=None, **repository_options):
    clock = clock or Clock()
    repo = JobRepository(clock, **repository_options)
    reader = SimpleNamespace(read=Mock(return_value=PRIVATE))
    generator = generator or SimpleNamespace(
        question=AsyncMock(return_value=MockQuestion(question="另一个合成问题？", focus="合成验证")),
        report=AsyncMock(return_value=MockReport(summary="合成部分报告")))
    return MockInterviewJobs(repo, reader, generator, now_ms=clock), repo, reader, generator


def run(jobs):
    return asyncio.run(jobs.run_pending(user_id=OWNER, session_id=SESSION))


@pytest.mark.parametrize("now_ms,phase", [(DEADLINE - 100, "speaking"), (DEADLINE, "completed"), (DEADLINE + 1, "completed")])
def test_exact_deadline_fences_first_question_and_generates_only_one_report(now_ms, phase):
    jobs, repo, _, generator = harness(clock=Clock(now_ms))
    result = run(jobs)
    assert round_state(result).phase == phase
    assert generator.question.await_count == int(phase == "speaking")
    assert generator.report.await_count == int(phase == "completed")
    assert len(repo.claims) <= 2
    assert repo.record["data"]["provider_failures"] == 0
    assert repo.record["data"]["deadline_at_ms"] == DEADLINE


def test_question_finishing_one_millisecond_before_deadline_is_accepted():
    clock = Clock(DEADLINE - 100)
    async def question(**_):
        clock.value = DEADLINE - 1
        return MockQuestion(question="截止前的合成题目？", focus="合成边界")
    generator = SimpleNamespace(question=AsyncMock(side_effect=question), report=AsyncMock())
    jobs, repo, _, _ = harness(clock=clock, generator=generator)
    result = run(jobs)
    assert round_state(result).phase == "speaking"
    assert round_state(result).rounds[-1].question == "截止前的合成题目？"
    assert repo.finishes[0]["now_ms"] == DEADLINE - 1
    generator.report.assert_not_awaited()


def test_midnight_before_fixed_deadline_does_not_end_or_restart_job():
    midnight = START + 30 * 60 * 1000
    jobs, repo, _, generator = harness(clock=Clock(midnight))
    result = run(jobs)
    assert round_state(result).phase == "speaking"
    generator.question.assert_awaited_once()
    generator.report.assert_not_awaited()
    assert repo.record["data"]["deadline_at_ms"] == DEADLINE


def test_expiry_between_snapshot_and_claim_uses_new_report_operation():
    clock = Clock(DEADLINE - 100)
    jobs, repo, _, generator = harness(clock=clock, answered=True)
    old_operation = round_state(repo.record).operation_id
    repo.after_get = lambda: setattr(clock, "value", DEADLINE)
    result = run(jobs)
    assert round_state(result).phase == "completed"
    generator.question.assert_not_awaited()
    generator.report.assert_awaited_once()
    assert repo.claims[0][0] == old_operation
    assert repo.claims[1][0] != old_operation
    assert len(round_state(result).rounds) == 1


def test_another_expiry_worker_racing_claim_cannot_launch_stale_question():
    clock = Clock(DEADLINE - 100)
    jobs, repo, _, generator = harness(clock=clock)
    def expire_elsewhere():
        clock.value = DEADLINE
        repo.expire_duration(user_id=OWNER, session_id=SESSION, now_ms=DEADLINE)
    repo.before_claim = expire_elsewhere
    assert round_state(run(jobs)).phase == "completed"
    generator.question.assert_not_awaited()
    generator.report.assert_awaited_once()


def test_question_result_at_deadline_is_discarded_then_report_completes():
    clock = Clock(DEADLINE - 100)
    async def question(**_):
        clock.value = DEADLINE
        return MockQuestion(question="不得发布的合成迟到题目？", focus="合成测试")
    generator = SimpleNamespace(question=AsyncMock(side_effect=question),
                                report=AsyncMock(return_value=MockReport(summary="合成部分报告")))
    jobs, repo, _, _ = harness(clock=clock, generator=generator, answered=True)
    result = run(jobs)
    assert round_state(result).phase == "completed"
    assert len(round_state(result).rounds) == 1
    assert all("迟到" not in item.question for item in round_state(result).rounds)
    generator.question.assert_awaited_once()
    generator.report.assert_awaited_once()
    assert len(repo.finishes) == 2
    assert repo.record["data"]["provider_failures"] == 0


def test_result_racing_already_committed_expiry_recovers_report():
    clock = Clock(DEADLINE - 100)
    jobs, repo, _, generator = harness(clock=clock, answered=True)
    def expire_elsewhere():
        clock.value = DEADLINE
        repo.expire_duration(user_id=OWNER, session_id=SESSION, now_ms=DEADLINE)
    repo.before_finish = expire_elsewhere
    result = run(jobs)
    assert round_state(result).phase == "completed"
    assert len(round_state(result).rounds) == 1
    generator.question.assert_awaited_once()
    generator.report.assert_awaited_once()
    assert repo.record["data"]["provider_failures"] == 0


def test_expired_job_waits_for_another_workers_report_claim():
    clock = Clock(DEADLINE)
    jobs, repo, _, generator = harness(clock=clock)
    ordinary_claim = repo.claim_generation
    calls = 0
    def competing_claim(**values):
        nonlocal calls
        calls += 1
        if calls == 2:
            ordinary_claim(**values)
        return ordinary_claim(**values)
    repo.claim_generation = competing_claim
    result = run(jobs)
    assert round_state(result).phase == "generating_report"
    assert result["data"]["generation_claim"] is not None
    generator.question.assert_not_awaited()
    generator.report.assert_not_awaited()


def test_deadline_bounds_provider_wait_without_incrementing_faults():
    async def never_finishes(**_):
        await asyncio.Event().wait()
    clock = Clock(DEADLINE - 25)
    generator = SimpleNamespace(question=AsyncMock(side_effect=never_finishes),
                                report=AsyncMock(return_value=MockReport(summary="合成到期报告")))
    jobs, repo, _, _ = harness(clock=clock, generator=generator)
    async def scenario():
        return await asyncio.wait_for(jobs.run_pending(user_id=OWNER, session_id=SESSION), .5)
    result = asyncio.run(scenario())
    assert round_state(result).phase == "completed"
    assert repo.expiries == [DEADLINE]
    assert all(not values.get("failed") for values in repo.finishes)
    assert repo.record["data"]["provider_failures"] == 0
    generator.report.assert_awaited_once()


def test_provider_timeout_before_deadline_does_not_pretend_duration_expired():
    generator = SimpleNamespace(question=AsyncMock(side_effect=TimeoutError()), report=AsyncMock())
    jobs, repo, _, _ = harness(clock=Clock(DEADLINE - 200), generator=generator)
    result = run(jobs)
    assert round_state(result).phase == "generating_question"
    assert result["data"]["end_reason"] is None
    assert result["data"]["provider_failures"] == 1
    assert repo.expiries == []
    generator.report.assert_not_awaited()


def test_resume_read_crossing_deadline_never_calls_question_model():
    clock = Clock(DEADLINE - 10)
    jobs, repo, reader, generator = harness(clock=clock)
    def read(**_):
        clock.value = DEADLINE
        return PRIVATE
    reader.read.side_effect = read
    assert round_state(run(jobs)).phase == "completed"
    generator.question.assert_not_awaited()
    generator.report.assert_awaited_once()
    assert repo.record["data"]["provider_failures"] == 0


def test_no_answer_expiry_report_has_no_model_call_and_no_score():
    clock = Clock(DEADLINE)
    jobs, repo, reader, _ = harness(clock=clock)
    generator = MockInterviewGenerator(repo.settings)
    generator._generate = AsyncMock(side_effect=AssertionError("no model expected"))
    jobs.generator = generator
    result = run(jobs)
    assert round_state(result).phase == "completed"
    assert result["data"]["report"]["overall_score"] is None
    assert result["data"]["report"]["dimensions"] is None
    assert result["data"]["report"]["feedback"] == []
    reader.read.assert_not_called()
    generator._generate.assert_not_awaited()


def test_expiry_provider_error_is_lifecycle_event_with_private_diagnostics_hidden(caplog, monkeypatch):
    clock = Clock(DEADLINE - 10)
    async def fault_after_deadline(**_):
        clock.value = DEADLINE
        raise MockGenerationUnavailable(PRIVATE, error_category="provider_http_error")
    generator = SimpleNamespace(question=AsyncMock(side_effect=fault_after_deadline),
                                report=AsyncMock(return_value=MockReport(summary="合成报告")))
    jobs, repo, _, _ = harness(clock=clock, generator=generator)
    # API tests configure service handlers before this file. Capture each real
    # log emission once rather than attaching the same handler at two levels.
    monkeypatch.setattr(logging.getLogger(LOGGER_NAME), "handlers", [caplog.handler])
    monkeypatch.setattr(logging.getLogger(LOGGER_NAME), "propagate", False)
    caplog.set_level(logging.INFO, logger=LOGGER_NAME)
    assert round_state(run(jobs)).phase == "completed"
    events = [json.loads(entry.message) for entry in caplog.records if "mock_interview.generation_stage" in entry.message]
    assert PRIVATE not in json.dumps(events)
    assert OWNER not in json.dumps(events) and SESSION not in json.dumps(events)
    totals = [event for event in events if event["stage"] == "generation_total"]
    assert [(event["kind"], event["outcome"]) for event in totals] == [("question", "cancelled"), ("report", "success")]
    assert len({event["diagnostic_id"] for event in totals}) == 2
    assert repo.record["data"]["provider_failures"] == 0


def test_cancelled_question_expires_before_cleanup_and_preserves_new_report_claim():
    async def scenario():
        entered = asyncio.Event()
        clock = Clock(DEADLINE - 100)
        async def wait_for_cancel(**_):
            entered.set()
            await asyncio.Event().wait()
        jobs, repo, _, _ = harness(clock=clock, generator=SimpleNamespace(question=wait_for_cancel))
        task = asyncio.create_task(jobs.run_pending(user_id=OWNER, session_id=SESSION))
        await asyncio.wait_for(entered.wait(), .5)
        clock.value = DEADLINE
        ended = repo.expire_duration(user_id=OWNER, session_id=SESSION, now_ms=DEADLINE)
        claimed = repo.claim_generation(user_id=OWNER, session_id=SESSION,
                                       operation_id=round_state(ended).operation_id, now_ms=DEADLINE)
        report_claim = claimed["data"]["generation_claim"]
        task.cancel()
        with pytest.raises(asyncio.CancelledError):
            await task
        assert repo.record["data"]["generation_claim"] == report_claim
        assert repo.finishes == []
        assert repo.record["data"]["provider_failures"] == 0
    asyncio.run(scenario())


def test_ordinary_claim_conflict_retains_error_without_provider_call():
    jobs, repo, _, generator = harness()
    repo.record["data"]["generation_claim"] = "synthetic-other-worker"
    with pytest.raises(DomainRequestError) as caught:
        run(jobs)
    assert caught.value.error_code == "mock_generation_in_progress"
    generator.question.assert_not_awaited()
    assert repo.finishes == []


def test_cancelled_deleted_question_retains_cancellation():
    async def scenario():
        entered = asyncio.Event()
        clock = Clock(DEADLINE - 100)
        async def wait_for_cancel(**_):
            entered.set()
            await asyncio.Event().wait()
        jobs, repo, _, _ = harness(clock=clock, generator=SimpleNamespace(question=wait_for_cancel))
        task = asyncio.create_task(jobs.run_pending(user_id=OWNER, session_id=SESSION))
        await asyncio.wait_for(entered.wait(), .5)
        clock.value = DEADLINE
        repo.expire_duration = Mock(side_effect=DomainRequestError(
            "mock-interview", "expire", "合成记录已删除", 404, "mock_not_found"))
        task.cancel()
        with pytest.raises(asyncio.CancelledError):
            await task
        assert repo.finishes == []
    asyncio.run(scenario())


def test_global_has_no_duration_fence_even_after_cn_deadline():
    clock = Clock(DEADLINE + 100)
    jobs, repo, _, generator = harness(clock=clock, deadline=None, edition="global")
    assert round_state(run(jobs)).phase == "speaking"
    generator.question.assert_awaited_once()
    generator.report.assert_not_awaited()
    assert repo.expiries == []
    assert len(repo.claims) == 1


def test_report_model_completion_after_deadline_remains_allowed():
    clock = Clock(DEADLINE - 1)
    async def report(**_):
        clock.value = DEADLINE + 100
        return MockReport(summary="合成报告可在截止后完成")
    generator = SimpleNamespace(question=AsyncMock(), report=AsyncMock(side_effect=report))
    jobs, repo, _, _ = harness(clock=clock, generator=generator, answered=True, report=True)
    result = run(jobs)
    assert round_state(result).phase == "completed"
    assert result["data"]["report"]["summary"] == "合成报告可在截止后完成"
    generator.question.assert_not_awaited()
    generator.report.assert_awaited_once()
    assert repo.expiries == []
