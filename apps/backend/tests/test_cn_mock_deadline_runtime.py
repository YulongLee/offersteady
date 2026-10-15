"""Synthetic server clocks and providers: no minute waits, audio or model calls."""
import asyncio
from copy import deepcopy
from dataclasses import asdict
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock

import pytest

from app.services.mock_interview_rounds import MockRoundState
from app.services.mock_interview_runtime import MockController, MockInterviewRuntime, public_mock


def make_record(phase="listening", *, deadline=3_601_000):
    state = MockRoundState().start()
    if phase != "generating_question":
        state = state.publish_question(state.operation_id, "合成问题：如何处理重复请求？")
        if phase in ("listening", "paused"):
            state = state.listen(state.rounds[-1].question_id, 1000)
        if phase == "paused":
            state = state.pause()
    return {"session_id": "synthetic-mock", "owner_user_id": "synthetic-owner",
        "billing_class": "points", "refunded": False, "created_at_ms": 1000,
        "data": {"title": "合成练习", "target_role": "测试工程师", "state": asdict(state),
            "billable_ms": 0, "billed_minutes": 0, "clock_at_ms": 1000 if phase == "listening" else None,
            "lease_until_ms": deadline + 15_000 if deadline else 9_000_000,
            "control_token": "synthetic-token", "started_at_ms": 1000,
            "deadline_at_ms": deadline, "duration_limit_ms": 3_600_000 if deadline else None,
            "end_reason": None, "generation_claim": None}}


class Repository:
    def __init__(self, record):
        self.record = deepcopy(record)
        self.expirations = 0
        self.meter_calls = 0

    def duration_deadline(self, record):
        return record["data"].get("deadline_at_ms")

    def expire_duration(self, *, now_ms, **kwargs):
        self.expirations += 1
        from app.services.mock_interview_repository import round_state
        state = round_state(self.record)
        if self.duration_deadline(self.record) <= now_ms and state.phase not in ("completed", "generating_report"):
            self.record["data"].update(state=asdict(state.end()), end_reason="time_limit", clock_at_ms=None,
                                       generation_claim=None)
        return deepcopy(self.record)

    def control_tick(self, *, now_ms, active=None, **kwargs):
        self.meter_calls += 1
        data = self.record["data"]
        data["lease_until_ms"] = now_ms + 15_000
        if active is not None:
            data["clock_at_ms"] = now_ms if active else None
        return deepcopy(self.record)

    def acquire_control(self, **kwargs):
        return deepcopy(self.record)

    def recovery_candidates(self, **kwargs):
        return []

    def release_control(self, **kwargs):
        self.record["data"].update(control_token=None, lease_until_ms=0, clock_at_ms=None)
        return deepcopy(self.record)


def setup(phase="listening", *, deadline=3_601_000):
    record = make_record(phase, deadline=deadline)
    repository = Repository(record)
    clock = [deadline or 3_601_000]
    audio = SimpleNamespace(revoke=Mock(return_value=None), renew=Mock(), open=Mock())
    realtime = SimpleNamespace(terminate_session_for_admin=Mock(),
                               record_web_session_heartbeat=Mock())
    runtime = MockInterviewRuntime(repository, None, None, None, audio, realtime, now_ms=lambda: clock[0])
    runtime._generate = Mock()
    send = AsyncMock()
    controller = MockController("synthetic-owner", "synthetic-mock", "synthetic-token", record, send)
    runtime.controllers[controller.session_id] = controller
    return runtime, controller, repository, clock


@pytest.mark.parametrize("phase", ["listening", "speaking", "paused", "generating_question"])
def test_reaper_ends_every_phase_at_exact_deadline_and_retires_once(phase):
    async def run():
        runtime, controller, repository, _ = setup(phase)
        try:
            await runtime.reap()
            assert controller.duration_ended
            assert controller.record["data"]["state"]["phase"] == "generating_report"
            assert controller.record["data"]["end_reason"] == "time_limit"
            assert controller.record["data"]["clock_at_ms"] is None
            runtime.audio.revoke.assert_called_once_with(controller.session_id)
            runtime.realtime.terminate_session_for_admin.assert_called_once()
            runtime._generate.assert_called_once_with(controller)
            assert controller.send.call_args.args[0]["session"]["endReason"] == "time_limit"
            await runtime.reap()
            runtime._generate.assert_called_once()
            assert repository.expirations == 1
        finally:
            await runtime.shutdown()
    asyncio.run(run())


@pytest.mark.parametrize("entry", ["heartbeat", "command", "capture"])
def test_expired_commands_and_capture_cannot_resume_or_consume_more_time(entry):
    async def run():
        runtime, controller, repository, _ = setup()
        try:
            if entry == "heartbeat":
                await runtime.heartbeat(controller)
            elif entry == "command":
                await runtime.command(controller, action="submit", version=controller.record["data"]["state"]["version"],
                    question_id="synthetic-stale-question", answer="合成回答", submission_id="synthetic-submit")
            else:
                await runtime._open_capture(controller)
            assert repository.meter_calls == 0
            assert controller.record["data"]["state"]["phase"] == "generating_report"
            runtime.audio.open.assert_not_called()
        finally:
            await runtime.shutdown()
    asyncio.run(run())


def test_expiry_cancels_question_and_speech_but_starts_only_one_report():
    async def run():
        runtime, controller, _, _ = setup("speaking")
        async def blocked():
            await asyncio.Event().wait()
        controller.generation = asyncio.create_task(blocked())
        controller.speech = asyncio.create_task(blocked())
        try:
            await runtime.reap()
            assert controller.generation.cancelled() and controller.speech.cancelled()
            runtime._generate.assert_called_once()
        finally:
            await runtime.shutdown()
    asyncio.run(run())


def test_transient_binding_cleanup_failure_does_not_strand_expired_report():
    async def run():
        runtime, controller, _, _ = setup("paused")
        runtime.realtime.terminate_session_for_admin.side_effect = [RuntimeError("synthetic cleanup failure"), None]
        try:
            with pytest.raises(RuntimeError, match="synthetic cleanup failure"):
                await runtime.reap()
            assert controller.record["data"]["end_reason"] == "time_limit"
            assert not controller.duration_ended and not controller.binding_released
            runtime._generate.assert_not_called()
            await runtime.reap()
            assert controller.duration_ended and controller.binding_released
            runtime._generate.assert_called_once_with(controller)
        finally:
            await runtime.shutdown()
    asyncio.run(run())


def test_reconnecting_after_deadline_ends_instead_of_pausing_with_new_time():
    async def run():
        runtime, controller, _, _ = setup()
        runtime.controllers.clear()
        try:
            reconnected = await runtime.attach(user_id=controller.user_id, session_id=controller.session_id, send=AsyncMock())
            assert reconnected.record["data"]["deadline_at_ms"] == 3_601_000
            assert reconnected.duration_ended
            assert reconnected.record["data"]["state"]["phase"] == "generating_report"
        finally:
            await runtime.shutdown()
    asyncio.run(run())


def test_no_expiry_before_boundary_and_no_cn_duration_policy_for_global():
    async def run():
        for deadline in (3_601_000, None):
            runtime, controller, repository, clock = setup("paused", deadline=deadline)
            clock[0] = 3_600_999 if deadline else 20_000_000
            controller.record["data"]["lease_until_ms"] = clock[0] + 15_000
            try:
                await runtime.reap()
                assert repository.expirations == 0
                assert not controller.duration_ended
                assert controller.record["data"]["state"]["phase"] == "paused"
            finally:
                await runtime.shutdown()
    asyncio.run(run())


def test_late_drafts_are_dropped_and_public_timing_does_not_expose_control_credentials():
    async def run():
        runtime, controller, _, _ = setup()
        try:
            epoch = controller.record["data"]["state"]["capture_epoch"]
            runtime._draft(controller, epoch, "到期后迟到的合成转写")
            assert controller.draft is None
            controller.draft = (epoch, "截止前尚未提交的合成转写")
            await runtime.flush_draft(controller)
            controller.send.assert_not_awaited()
            payload = public_mock(controller.record)
            assert payload["startedAtMs"] == 1000 and payload["deadlineAtMs"] == 3_601_000
            assert payload["durationLimitMinutes"] == 60
            assert "control_token" not in str(payload) and "synthetic-token" not in str(payload)
        finally:
            await runtime.shutdown()
    asyncio.run(run())
