"""Synthetic runtime policy controls; no database, audio or provider calls."""
import asyncio
from copy import deepcopy
from dataclasses import asdict
from threading import Event
from unittest.mock import AsyncMock, Mock

import pytest

from app.core.config import Settings
from app.services.mock_interview_audio import MockInterviewAudio
from app.services.mock_interview_repository import round_state
from app.services.mock_interview_runtime import MockController, MockInterviewRuntime
from test_cn_mock_deadline_runtime import make_record


def runtime_for(edition, *, phase="listening"):
    row = make_record(phase, deadline=None)
    repo = Mock()
    repo.settings = Settings(_env_file=None, environment="test", product_edition=edition)
    repo.duration_deadline.return_value = None
    repo.control_tick.side_effect = lambda **_: deepcopy(row)
    def transition(*, move, **_):
        following = move(round_state(row))
        row["data"]["state"] = asdict(following)
        row["data"]["clock_at_ms"] = 1000 if following.phase == "listening" else None
        return deepcopy(row)
    repo.transition.side_effect = transition
    gateway = Mock()
    audio = MockInterviewAudio(gateway_factory=lambda: gateway, now_ms=lambda: 1000)
    runtime = MockInterviewRuntime(repo, None, None, None, audio, Mock(), now_ms=lambda: 1000)
    runtime._generate = Mock()
    controller = MockController(row["owner_user_id"], row["session_id"], "synthetic-token", row, AsyncMock())
    runtime.controllers[controller.session_id] = controller
    return runtime, controller, gateway


@pytest.mark.parametrize("edition", ["cn", "global"])
def test_only_cn_submit_proceeds_while_actual_close_remains_pending(edition):
    async def run():
        runtime, controller, gateway = runtime_for(edition)
        started, release = Event(), Event()
        def close(**_):
            started.set()
            assert release.wait(5)
        gateway.close_session.side_effect = close
        state = round_state(controller.record)
        old = runtime.audio.open(session_id=controller.session_id, owner_id=controller.user_id,
            device_id="synthetic-device", epoch=state.capture_epoch, deadline_ms=2000, sink=lambda *_: None)
        task = asyncio.create_task(runtime.command(controller, action="submit", version=state.version,
            question_id=state.rounds[-1].question_id, answer="合成已确认回答", submission_id="synthetic-submit"))
        try:
            assert await asyncio.to_thread(started.wait, 2)
            if edition == "cn":
                await asyncio.wait_for(asyncio.shield(task), 1)
                runtime._generate.assert_called_once_with(controller)
                assert controller.send.call_args.args[0]["session"]["state"]["phase"] == "generating_question"
            else:
                await asyncio.sleep(0)
                assert not task.done()
                runtime._generate.assert_not_called()
            assert old.revoked and not old.closed
            assert len(runtime._capture_closes) == 1
            release.set()
            await asyncio.wait_for(task, 1)
            await runtime._drain_capture_closes(controller.capture_closes)
            assert old.closed and not runtime._capture_closes
        finally:
            release.set()
            await asyncio.gather(task, return_exceptions=True)
            await runtime.shutdown()
    asyncio.run(run())


@pytest.mark.parametrize("edition", ["cn", "global"])
@pytest.mark.parametrize("action,phase", [("listen", "speaking"), ("resume", "paused")])
def test_only_cn_new_answer_ignores_unrelated_detached_close(edition, action, phase):
    async def run():
        runtime, controller, gateway = runtime_for(edition, phase=phase)
        started, release = Event(), Event()
        def close(**_):
            started.set()
            assert release.wait(5)
        gateway.close_session.side_effect = close
        old = runtime.audio.open(session_id=controller.session_id, owner_id=controller.user_id,
            device_id="synthetic-device", epoch="a" * 32, deadline_ms=2000, sink=lambda *_: None)
        runtime._open_capture = AsyncMock()
        await runtime._close_capture(controller, wait=False)
        state = round_state(controller.record)
        kwargs = {"question_id": state.rounds[-1].question_id} if action == "listen" else {}
        task = asyncio.create_task(runtime.command(controller, action=action, version=state.version, **kwargs))
        try:
            assert await asyncio.to_thread(started.wait, 2)
            if edition == "cn":
                await asyncio.wait_for(asyncio.shield(task), 1)
                runtime._open_capture.assert_awaited_once_with(controller)
            else:
                await asyncio.sleep(0)
                assert not task.done()
                runtime._open_capture.assert_not_awaited()
            assert old.revoked and not old.closed
            assert len(runtime._capture_closes) == 1
            release.set()
            await asyncio.wait_for(task, 1)
            await runtime._drain_capture_closes(controller.capture_closes)
            runtime._open_capture.assert_awaited_once_with(controller)
            assert old.closed and not runtime._capture_closes
        finally:
            release.set()
            await asyncio.gather(task, return_exceptions=True)
            await runtime.shutdown()
    asyncio.run(run())


@pytest.mark.parametrize("edition", ["cn", "global"])
def test_capture_diagnostics_cannot_break_release_and_stay_cn_only(monkeypatch, edition):
    events = []
    def failing_log(*_, **fields):
        events.append(fields)
        raise RuntimeError("synthetic-private-log-failure")
    monkeypatch.setattr("app.services.mock_interview_runtime.log_event", failing_log)
    async def run():
        runtime, controller, gateway = runtime_for(edition)
        state = round_state(controller.record)
        old = runtime.audio.open(session_id=controller.session_id, owner_id=controller.user_id,
            device_id="synthetic-device", epoch=state.capture_epoch, deadline_ms=2000, sink=lambda *_: None)
        try:
            await runtime._close_capture(controller)
            assert old.revoked and old.closed
            assert not runtime._capture_closes and not controller.capture_closes and not runtime.audio._closing
            gateway.close_session.assert_called_once()
            assert len(events) == (1 if edition == "cn" else 0)
        finally:
            await runtime.shutdown()
    asyncio.run(run())
