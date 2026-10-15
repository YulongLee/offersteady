"""Real durable expiry with synthetic users, clocks and mocked providers only."""
import asyncio
from unittest.mock import AsyncMock

import pytest

from app.services.mock_interview_repository import round_state
from app.services.mock_interview_runtime import MockInterviewRuntime
from test_mock_interview_postgres import DATABASE_URL, mock_runtime_fixture
from test_cn_mock_flat_billing_postgres import repositories


pytestmark = pytest.mark.skipif(not DATABASE_URL, reason="Isolated PostgreSQL required")


@pytest.mark.parametrize("phase", ["listening", "speaking", "paused", "generating_question"])
def test_real_reaper_persists_sixty_minute_end_and_report_without_extra_charge(repositories, phase):
    async def run():
        runtime, user, sid, clock, generator, billing = mock_runtime_fixture(repositories)
        entered = asyncio.Event()
        async def blocked_question(**kwargs):
            entered.set()
            await asyncio.Event().wait()
        if phase == "generating_question":
            generator.question.side_effect = blocked_question
        controller = await runtime.attach(user_id=user, session_id=sid, send=AsyncMock())
        runtime.desktops[sid] = ("device", AsyncMock())
        try:
            started = clock[0]
            await runtime.command(controller, action="start", version=round_state(controller.record).version)
            if phase == "generating_question":
                await asyncio.wait_for(entered.wait(), 2)
            else:
                await controller.generation
                if phase in ("listening", "paused"):
                    state = round_state(controller.record)
                    await runtime.command(controller, action="listen", version=state.version,
                        question_id=state.rounds[-1].question_id)
                if phase == "paused":
                    await runtime.command(controller, action="pause", version=round_state(controller.record).version)
            assert controller.record["data"]["deadline_at_ms"] == started + 3_600_000
            # The control lease is also expired. Deadline handling must run
            # before detach, and must not depend on a billable clock existing.
            clock[0] = started + 3_600_000
            await runtime.reap()
            await asyncio.wait_for(controller.generation, 3)
            saved = runtime.repository.get(user_id=user, session_id=sid)
            assert round_state(saved).phase == "completed"
            assert saved["data"]["end_reason"] == "time_limit"
            assert saved["data"]["deadline_at_ms"] == clock[0]
            assert saved["data"]["report"]["overall_score"] is None
            assert saved["data"]["billed_minutes"] == 0
            assert runtime.audio.snapshot()["captures"] == 0
            runtime.realtime.terminate_session_for_admin.assert_called_once()
            assert billing.state_for_user(user_id=user).balance == 100
            with runtime.repository.connect() as conn:
                base = conn.execute("SELECT status,ended_at_ms FROM interview_sessions WHERE session_id=%s", (sid,)).fetchone()
                debits = conn.execute("SELECT kind,points FROM points_redemption_ledger WHERE user_id=%s AND reference_id LIKE %s", (user, f"mock:{sid}:%")).fetchall()
            assert base == {"status": "ended", "ended_at_ms": clock[0]}
            assert debits == [{"kind": "mock_interview_entry_settlement", "points": -100}]
        finally:
            await runtime.shutdown()
    asyncio.run(run())


def test_new_process_reconnect_retains_original_start_and_completes_expired_session(repositories):
    async def run():
        old, user, sid, clock, generator, _ = mock_runtime_fixture(repositories)
        started = clock[0]
        controller = await old.attach(user_id=user, session_id=sid, send=AsyncMock())
        await old.command(controller, action="start", version=round_state(controller.record).version)
        await controller.generation
        await old.shutdown()
        clock[0] = started + 3_600_500
        fresh = MockInterviewRuntime(old.repository, old.reader, old.jobs, old.tts, old.audio,
            old.realtime, now_ms=lambda: clock[0])
        try:
            restored = await fresh.attach(user_id=user, session_id=sid, send=AsyncMock())
            assert restored.record["data"]["deadline_at_ms"] == started + 3_600_000
            assert restored.duration_ended
            await asyncio.wait_for(restored.generation, 3)
            assert round_state(fresh.repository.get(user_id=user, session_id=sid)).phase == "completed"
            assert generator.question.await_count == 1
        finally:
            await fresh.shutdown()
    asyncio.run(run())


def test_deadline_preserves_only_completed_answers_for_partial_report(repositories):
    async def run():
        runtime, user, sid, clock, generator, _ = mock_runtime_fixture(repositories)
        controller = await runtime.attach(user_id=user, session_id=sid, send=AsyncMock())
        runtime.desktops[sid] = ("device", AsyncMock())
        try:
            await runtime.command(controller, action="start", version=round_state(controller.record).version)
            await controller.generation
            state = round_state(controller.record)
            await runtime.command(controller, action="listen", version=state.version,
                question_id=state.rounds[-1].question_id)
            generator.question.return_value = generator.question.return_value.model_copy(update={"question": "合成问题：怎样避免重复执行？"})
            state = round_state(controller.record)
            await runtime.command(controller, action="submit", version=state.version,
                question_id=state.rounds[-1].question_id, answer="合成回答：使用唯一约束和幂等键。", submission_id="synthetic-answer")
            await controller.generation
            controller.draft = ("synthetic-draft", "未提交的合成回答不能进入报告。")
            clock[0] = controller.record["data"]["deadline_at_ms"]
            await runtime.reap()
            await asyncio.wait_for(controller.generation, 3)
            rounds = generator.report.call_args.kwargs["rounds"]
            assert len(rounds) == 2 and rounds[0].answer == "合成回答：使用唯一约束和幂等键。"
            assert rounds[1].answer is None
            assert controller.draft is None
        finally:
            await runtime.shutdown()
    asyncio.run(run())


@pytest.mark.parametrize("report_failed", [False, True])
def test_new_process_recovers_pending_time_limit_report_but_not_real_provider_failure(repositories, report_failed):
    async def run():
        old, user, sid, clock, generator, _ = mock_runtime_fixture(repositories)
        controller = await old.attach(user_id=user, session_id=sid, send=AsyncMock())
        await old.command(controller, action="start", version=round_state(controller.record).version)
        await controller.generation
        clock[0] = controller.record["data"]["deadline_at_ms"]
        pending = old.repository.expire_duration(user_id=user, session_id=sid, now_ms=clock[0])
        report_operation = round_state(pending).operation_id
        claimed = old.repository.claim_generation(user_id=user, session_id=sid,
            operation_id=report_operation, now_ms=clock[0])
        old_claim = claimed["data"]["generation_claim"]
        if report_failed:
            old.repository.finish_generation(user_id=user, session_id=sid, operation_id=report_operation,
                claim_id=old_claim, now_ms=clock[0], failed=True)
        # Simulate a process that died after durable expiry/claim and before any
        # report output. The pending report claim remains unless already failed.
        await old.shutdown()
        clock[0] += 16_000
        fresh = MockInterviewRuntime(old.repository, old.reader, old.jobs, old.tts, old.audio,
            old.realtime, now_ms=lambda: clock[0])
        try:
            restored = await fresh.attach(user_id=user, session_id=sid, send=AsyncMock())
            assert restored.duration_ended and restored.record["data"]["end_reason"] == "time_limit"
            if report_failed:
                assert restored.generation is None
                generator.report.assert_not_awaited()
                await fresh.command(restored, action="retry", version=round_state(restored.record).version)
            else:
                assert round_state(restored.record).operation_id != report_operation
            await asyncio.wait_for(restored.generation, 3)
            saved = fresh.repository.get(user_id=user, session_id=sid)
            assert round_state(saved).phase == "completed"
            generator.report.assert_awaited_once()
            assert saved["data"]["deadline_at_ms"] == pending["data"]["deadline_at_ms"]
        finally:
            await fresh.shutdown()
    asyncio.run(run())
