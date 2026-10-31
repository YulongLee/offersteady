"""Blocked synthetic providers + isolated PG; no remote audio/model calls."""
import asyncio
import json
from concurrent.futures import ThreadPoolExecutor
from threading import Event
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock

import pytest
from starlette.websockets import WebSocketDisconnect

from app.core.config import Settings
from app.core.errors import DomainRequestError
from app.modules import mock_interview as api
from app.ports.realtime_speech import TranscriptResult
from app.schemas.mock_interview import MockQuestion
from app.services.mock_interview_audio import MockInterviewAudio
from app.services.mock_interview_repository import round_state
from app.services.mock_interview_runtime import MockInterviewRuntime
from test_mock_interview_postgres import DATABASE_URL, mock_runtime_fixture, repositories


pytestmark = pytest.mark.skipif(not DATABASE_URL, reason="Isolated PostgreSQL required")


async def listening_runtime(repositories):
    runtime, user, sid, now, generator, billing = mock_runtime_fixture(repositories)
    gateways = []
    def factory():
        gateway = Mock()
        gateway.transcribe.return_value = TranscriptResult("合成旧轮回答", .9)
        gateways.append(gateway)
        return gateway
    runtime.audio = MockInterviewAudio(gateway_factory=factory, now_ms=lambda: now[0])
    messages, desktop_messages = [], []
    async def send(value):
        messages.append(value)
    async def desktop_send(value):
        desktop_messages.append(value)
    controller = await runtime.attach(user_id=user, session_id=sid, send=send)
    runtime.desktops[sid] = ("device", desktop_send)
    await runtime.command(controller, action="start", version=round_state(controller.record).version)
    await controller.generation
    state = round_state(controller.record)
    await runtime.command(controller, action="listen", version=state.version, question_id=state.rounds[-1].question_id)
    generator.question.return_value = MockQuestion(question="合成新轮：并发冲突怎么处理？", focus="并发")
    state = round_state(controller.record)
    submission = dict(action="submit", version=state.version, question_id=state.rounds[-1].question_id,
                      answer="我用合成幂等键与唯一约束处理重试。", submission_id="synthetic-answer-1")
    return runtime, controller, now, generator, gateways, messages, desktop_messages, submission, billing


def block_close(gateway):
    entered, release = Event(), Event()
    def close(**kwargs):
        entered.set()
        assert release.wait(5), "synthetic close was not released"
    gateway.close_session.side_effect = close
    return entered, release


async def entered(event):
    assert await asyncio.to_thread(event.wait, 2)


def test_submit_publishes_and_generates_while_old_close_blocks_without_duplicate_or_wait_billing(repositories):
    async def run():
        # One general worker makes an accidental shared-pool provider close
        # deterministically block the next DB/resume operation.
        asyncio.get_running_loop().set_default_executor(ThreadPoolExecutor(max_workers=1))
        runtime, controller, now, generator, gateways, messages, desktop_messages, submission, billing = await listening_runtime(repositories)
        sid = controller.session_id
        old = runtime.audio._captures[sid]
        closing, release = block_close(gateways[0])
        before_balance = billing.state_for_user(user_id=controller.user_id).balance
        try:
            now[0] += 1000
            await asyncio.wait_for(runtime.command(controller, **submission), 2)
            await entered(closing)
            assert not old.closed and old.revoked
            assert any(m.get("session", {}).get("state", {}).get("phase") == "generating_question" for m in messages)
            assert desktop_messages[-1] == {"type": "capture", "epoch": None}
            await asyncio.wait_for(controller.generation, 2)
            assert generator.question.await_count == 2
            assert len(round_state(controller.record).rounds) == 2
            assert controller.record["data"]["clock_at_ms"] is None
            now[0] += 10_000
            await asyncio.wait_for(runtime.command(controller, **submission), 2)
            assert generator.question.await_count == 2
            assert len(runtime._capture_closes) == 1
            assert controller.record["data"]["billable_ms"] == 1000
            assert billing.state_for_user(user_id=controller.user_id).balance == before_balance
            with pytest.raises(DomainRequestError):
                runtime.audio.ingest(session_id=sid, device_id="device", epoch=old.epoch, pcm=b"00")
        finally:
            release.set()
            await runtime.detach(controller)
        gateways[0].close_session.assert_called_once_with(session_id=old.provider_id)
        assert not runtime._capture_closes and not runtime.audio._closing
    asyncio.run(run())


def test_new_capture_uses_separate_adapter_and_old_callbacks_or_cleanup_cannot_change_it(repositories):
    async def run():
        runtime, controller, _, _, gateways, messages, _, submission, _ = await listening_runtime(repositories)
        sid = controller.session_id
        old = runtime.audio._captures[sid]
        await asyncio.to_thread(runtime.audio.ingest, session_id=sid, device_id="device", epoch=old.epoch, pcm=b"00")
        old_frame = gateways[0].transcribe.call_args.kwargs["frame"]
        closing, release = block_close(gateways[0])
        try:
            await runtime.command(controller, **submission)
            await entered(closing)
            await controller.generation
            state = round_state(controller.record)
            await asyncio.wait_for(runtime.command(controller, action="listen", version=state.version,
                question_id=state.rounds[-1].question_id), 2)
            new = runtime.audio._captures[sid]
            assert new.gateway is not old.gateway and new.epoch != old.epoch
            gateways[1].transcribe.return_value = TranscriptResult("合成新轮回答", .9)
            runtime.audio._partial(old_frame, TranscriptResult("不应出现的迟到回答", .9))
            runtime._draft(controller, old.epoch, "不应出现的排队旧回调")
            await asyncio.to_thread(runtime.audio.ingest, session_id=sid, device_id="device", epoch=new.epoch, pcm=b"00")
            await asyncio.sleep(0)
            await runtime.flush_draft(controller)
            assert messages[-1] == {"type": "transcript", "epoch": new.epoch, "text": "合成新轮回答"}
            release.set()
            await runtime._drain_capture_closes(controller.capture_closes)
            assert runtime.audio._captures[sid] is new and not new.closed
            gateways[1].close_session.assert_not_called()
            assert gateways[1].set_partial_listener.call_args.args[0] == runtime.audio._partial
        finally:
            release.set()
            await runtime.detach(controller)
        assert not runtime.audio._closing and not runtime._capture_closes
    asyncio.run(run())


@pytest.mark.parametrize("action", ["pause", "end", "detach"])
def test_pause_end_and_detach_drain_old_and_current_resources_after_nonblocking_submit(repositories, action):
    async def run():
        runtime, controller, _, _, gateways, _, _, submission, _ = await listening_runtime(repositories)
        closing, release = block_close(gateways[0])
        try:
            await runtime.command(controller, **submission)
            await entered(closing)
            await controller.generation
            state = round_state(controller.record)
            await runtime.command(controller, action="listen", version=state.version, question_id=state.rounds[-1].question_id)
            state = round_state(controller.record)
            if action == "detach":
                pending = asyncio.create_task(runtime.detach(controller))
            else:
                pending = asyncio.create_task(runtime.command(controller, action=action, version=state.version))
            # Durable stop precedes the upstream wait, not just eventual cleanup.
            for _ in range(100):
                durable = await runtime.db(runtime.repository.get, user_id=controller.user_id, session_id=controller.session_id)
                if durable["data"]["clock_at_ms"] is None:
                    break
                await asyncio.sleep(.01)
            assert durable["data"]["clock_at_ms"] is None
            assert not pending.done()
            release.set()
            await asyncio.wait_for(pending, 2)
            assert not runtime.audio._closing and not runtime._capture_closes
            assert runtime.audio.snapshot()["captures"] == 0
            if action == "pause":
                assert round_state(controller.record).phase == "paused"
            if action == "end":
                await controller.generation
                assert round_state(controller.record).phase == "completed"
        finally:
            release.set()
            await runtime.detach(controller)
        assert all(g.close_session.call_count == 1 for g in gateways)
    asyncio.run(run())


def test_drain_timeout_keeps_actual_close_tracked_until_release(repositories):
    async def run():
        runtime, controller, _, _, gateways, _, _, submission, _ = await listening_runtime(repositories)
        closing, release = block_close(gateways[0])
        runtime.capture_cleanup_wait_seconds = .01
        try:
            await runtime.command(controller, **submission)
            await entered(closing)
            await asyncio.wait_for(runtime.detach(controller), 1)
            assert not runtime.controllers
            assert len(runtime._capture_closes) == len(runtime.audio._closing) == 1
            task = next(iter(runtime._capture_closes))
            assert not task.cancelled()
            release.set()
            await task
            await asyncio.sleep(0)
            assert not runtime._capture_closes and not runtime.audio._closing
        finally:
            release.set()
            await runtime.shutdown()
    asyncio.run(run())


def test_capture_close_failure_records_only_fixed_operational_fields(repositories, monkeypatch):
    events = []
    monkeypatch.setattr("app.services.mock_interview_runtime.log_event",
        lambda logger, level, **fields: events.append(fields))
    async def run():
        runtime, controller, _, _, gateways, _, _, submission, _ = await listening_runtime(repositories)
        sensitive_marker = "synthetic-private-provider-body-and-key"
        gateways[0].close_session.side_effect = RuntimeError(sensitive_marker)
        await runtime.command(controller, **submission)
        await runtime._drain_capture_closes(controller.capture_closes)
        close_event = next(item for item in events if item["event"] == "mock_interview.capture_close")
        assert close_event["outcome"] == "failed" and close_event["error_code"] == "asr_close_failed"
        assert close_event["stage"] == "asr_close" and close_event["duration_ms"] >= 0
        operational_fields = {key: value for key, value in close_event.items() if key != "settings"}
        encoded = json.dumps(operational_fields)
        assert sensitive_marker not in encoded and controller.session_id not in encoded and controller.user_id not in encoded
        assert set(operational_fields) == {"event", "feature", "action", "stage", "duration_ms", "outcome", "error_code"}
        await runtime.detach(controller)
        assert not runtime._capture_closes and not runtime.audio._closing
    asyncio.run(run())


@pytest.mark.parametrize("cancel_index,before_observer_starts", [(0, False), (4, False), (4, True)])
def test_cancelled_active_or_queued_close_observer_still_releases_all_provider_resources(monkeypatch, cancel_index, before_observer_starts):
    events = []
    monkeypatch.setattr("app.services.mock_interview_runtime.log_event",
        lambda logger, level, **fields: events.append(fields))
    async def run():
        entered_events, release = [Event() for _ in range(4)], Event()
        gateways = []
        def factory():
            index = len(gateways)
            gateway = Mock()
            if index < 4:
                def close(**kwargs):
                    entered_events[index].set()
                    assert release.wait(5)
                gateway.close_session.side_effect = close
            gateways.append(gateway)
            return gateway
        audio = MockInterviewAudio(gateway_factory=factory, now_ms=lambda: 1000)
        repository = SimpleNamespace(settings=Settings(_env_file=None, environment="test", product_edition="cn"))
        runtime = MockInterviewRuntime(repository, None, None, None, audio, None, now_ms=lambda: 1000)
        controllers = []
        try:
            for index in range(5):
                controller = SimpleNamespace(session_id=f"synthetic-close-{index}", draft=None, capture_closes=set())
                controllers.append(controller)
                audio.open(session_id=controller.session_id, owner_id="synthetic", device_id="device",
                    epoch=f"{index:032x}", deadline_ms=2000, sink=lambda *_: None)
                await runtime._close_capture(controller, wait=False)
            observer = next(iter(controllers[cancel_index].capture_closes))
            if before_observer_starts:
                observer.cancel()
            for event in entered_events:
                await entered(event)
            actual = runtime._capture_closes[observer]
            if not before_observer_starts:
                observer.cancel()
            await asyncio.gather(observer, return_exceptions=True)
            assert observer.cancelled() and not actual.cancelled()
            assert len(runtime._capture_closes) == len(audio._closing) == 5
            assert events == []
            if cancel_index == 4:
                gateways[4].close_session.assert_not_called()
            # Drain must wait for actual work even when its observer is gone.
            draining = asyncio.create_task(runtime._drain_capture_closes(runtime._capture_closes))
            await asyncio.sleep(0)
            assert not draining.done()
            release.set()
            await asyncio.wait_for(draining, 2)
            await asyncio.sleep(0)
            assert not runtime._capture_closes and not audio._closing
            assert all(not controller.capture_closes for controller in controllers)
            assert all(gateway.close_session.call_count == 1 for gateway in gateways)
            assert len(events) == 5
            assert len([event for event in events if event["outcome"] == "cancelled"]) == 1
            assert all(event["error_code"] == "asr_close_observer_cancelled" for event in events if event["outcome"] == "cancelled")
        finally:
            release.set()
            await runtime.shutdown()
    asyncio.run(run())


class DisconnectedMicrophoneSocket:
    def __init__(self, *, on_receive=None):
        self.sent = []
        self.on_receive = on_receive

    async def accept(self):
        pass

    async def receive_text(self):
        return json.dumps({"deviceId": "device", "manualCode": "000000"})

    async def receive(self):
        if self.on_receive:
            self.on_receive()
        return {"type": "websocket.disconnect"}

    async def send_json(self, value):
        self.sent.append(value)

    async def close(self):
        raise WebSocketDisconnect(code=1006)


@pytest.mark.parametrize("replacement", [False, True])
def test_microphone_disconnected_close_is_safe_and_preserves_a_replacement(repositories, monkeypatch, replacement):
    async def run():
        runtime, controller, _, _, gateways, _, _, _, _ = await listening_runtime(repositories)
        sid = controller.session_id
        # The endpoint, rather than the setup helper, owns this registration.
        runtime.desktops.pop(sid)
        runtime.realtime.get_desktop_capture_binding.return_value = SimpleNamespace(session_id=sid, owner_user_id=controller.user_id)
        monkeypatch.setattr(api, "require_mock_runtime", lambda: runtime)
        newer = ("device", AsyncMock())
        socket = DisconnectedMicrophoneSocket(on_receive=(lambda: runtime.desktops.__setitem__(sid, newer)) if replacement else None)
        try:
            await api.mock_microphone(socket, sid)
            if replacement:
                assert runtime.desktops[sid] is newer
                assert round_state(controller.record).phase == "listening"
                gateways[0].close_session.assert_not_called()
            else:
                assert sid not in runtime.desktops
                assert round_state(controller.record).phase == "paused"
                assert controller.record["data"]["clock_at_ms"] is None
                gateways[0].close_session.assert_called_once()
        finally:
            await runtime.detach(controller)
    asyncio.run(run())
