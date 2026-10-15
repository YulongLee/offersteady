"""Synthetic inference protocol tests; never call a real provider or write audio."""
import asyncio
import base64
import json
from copy import deepcopy
from types import SimpleNamespace
from unittest.mock import AsyncMock
from uuid import UUID

import pytest

from app.core.config import Settings
from app.services.mock_interview_runtime import MockInterviewRuntime
from app.services.mock_interview_tts import MockInterviewTts, MockSpeechUnavailable


def event(kind, **payload):
    return {"header": {"event": kind, "task_id": "current"}, "payload": payload}


class Socket:
    def __init__(self, events):
        self.events = iter(events)
        self.sent = []
        self.closed = False

    async def __aenter__(self):
        return self

    async def __aexit__(self, *args):
        self.closed = True

    async def send(self, raw):
        self.sent.append(json.loads(raw))

    def __aiter__(self):
        return self

    async def __anext__(self):
        try:
            value = next(self.events)
        except StopIteration:
            raise StopAsyncIteration from None
        if isinstance(value, (str, bytes)):
            return value
        value = deepcopy(value)
        if isinstance(value.get("header"), dict) and value["header"].get("task_id") == "current":
            value["header"]["task_id"] = self.sent[0]["header"]["task_id"]
        return json.dumps(value)


def make(events, *, socket_type=Socket, **overrides):
    socket = socket_type(events)
    calls = []
    def connect(*args, **kwargs):
        calls.append((args, kwargs))
        return socket
    settings = Settings(_env_file=None, chat_qwen_api_key="synthetic-key",
        mock_interview_tts_model="qwen-audio-3.0-tts-plus", mock_interview_tts_voice="longanhuan_v3.6",
        mock_interview_tts_ws_url="wss://dashscope.aliyuncs.com/api-ws/v1/inference", **overrides)
    return MockInterviewTts(settings, connector=connect), socket, calls


async def collect(service):
    return b"".join([chunk async for chunk in service.stream("请介绍合成项目中的 Python 和数据库职责。")])


def test_inference_lifecycle_uses_exact_text_and_existing_pcm_format():
    service, socket, calls = make([
        event("task-started"), event("result-generated", output={"type": "sentence-begin"}),
        event("result-generated", output={"type": "sentence-synthesis"}), b"\0\0\1\0",
        event("result-generated", output={"type": "sentence-end"}), event("task-finished"),
    ])
    assert asyncio.run(collect(service)) == b"\0\0\1\0"
    assert [e["header"]["action"] for e in socket.sent] == ["run-task", "continue-task", "finish-task"]
    assert len({e["header"]["task_id"] for e in socket.sent}) == 1
    UUID(socket.sent[0]["header"]["task_id"])
    assert all(e["header"]["streaming"] == "duplex" for e in socket.sent)
    assert socket.sent[0]["payload"]["model"] == "qwen-audio-3.0-tts-plus"
    parameters = socket.sent[0]["payload"]["parameters"]
    assert parameters["format"] == "pcm" and parameters["sample_rate"] == 24000
    assert parameters["voice"] == "longanhuan_v3.6" and parameters["instruction"] == service._instructions
    assert socket.sent[1]["payload"]["input"]["text"] == "请介绍合成项目中的 Python 和数据库职责。"
    assert socket.sent[-1]["payload"] == {"input": {}}
    assert calls[0][0] == ("wss://dashscope.aliyuncs.com/api-ws/v1/inference",)
    assert calls[0][1]["additional_headers"] == {"Authorization": "Bearer synthetic-key"}
    assert socket.closed and service._slots._value == 2


@pytest.mark.parametrize("events", [
    [b"\0\0"], [event("task-finished")], [event("task-started"), event("task-started")],
    [event("task-started"), event("task-finished")],
    [event("task-started"), b"\0" , event("task-finished")],
    [event("result-generated", output={"type": "sentence-synthesis"})],
    [event("task-started"), event("result-generated", output=None)],
    [event("task-started"), event("result-generated", output={"type": "unexpected"})],
    [{"header": {"event": "task-started", "task_id": "different"}}],
    [event("unexpected")], [{"header": []}], ["[]"], ["null"], ["invalid-json"],
    [event("task-started")], [event("task-started"), b"\0\0"],
    [{"header": {"event": "task-failed", "task_id": "current", "error_message": "secret-provider-payload synthetic-key"}}],
])
def test_invalid_failure_and_early_close_are_redacted_and_release_capacity(events):
    service, socket, _ = make(events)
    with pytest.raises(MockSpeechUnavailable) as error:
        asyncio.run(collect(service))
    assert "secret-provider-payload" not in str(error.value) and "synthetic-key" not in str(error.value)
    assert socket.closed and service._slots._value == 2


def test_binary_frame_boundaries_do_not_split_pcm_samples():
    service, socket, _ = make([event("task-started"), b"\1", b"\0\2", b"\0", event("task-finished")])
    async def run():
        chunks = [chunk async for chunk in service.stream("合成测试")]
        assert all(len(chunk) % 2 == 0 for chunk in chunks)
        return b"".join(chunks)
    assert asyncio.run(run()) == b"\1\0\2\0" and socket.closed


@pytest.mark.parametrize("text", ["", " "*2, "合"*801])
def test_invalid_text_never_connects(text):
    service, _, calls = make([])
    async def run():
        return [chunk async for chunk in service.stream(text)]
    with pytest.raises(MockSpeechUnavailable):
        asyncio.run(run())
    assert not calls


def test_new_model_rejects_legacy_endpoint_without_connecting():
    service, _, calls = make([])
    service.settings = service.settings.model_copy(update={"mock_interview_tts_ws_url": "wss://dashscope.aliyuncs.com/api-ws/v1/realtime"})
    with pytest.raises(MockSpeechUnavailable, match="端点配置不匹配"):
        asyncio.run(collect(service))
    assert not calls


def test_overflow_and_consumer_close_release_socket_and_capacity():
    service, socket, _ = make([event("task-started"), b"00"*2])
    service.max_audio_bytes = 2
    with pytest.raises(MockSpeechUnavailable, match="时长限制"):
        asyncio.run(collect(service))
    assert socket.closed and service._slots._value == 2
    service, socket, _ = make([event("task-started"), b"00", b"00"])
    async def close():
        stream = service.stream("合成测试")
        assert await anext(stream) == b"00"
        await stream.aclose()
    asyncio.run(close())
    assert socket.closed and service._slots._value == 2


class SilentSocket(Socket):
    async def __anext__(self):
        await asyncio.Event().wait()


def test_provider_timeout_and_cancel_while_waiting_release_capacity():
    service, socket, _ = make([], socket_type=SilentSocket, mock_interview_provider_timeout_seconds=1)
    with pytest.raises(MockSpeechUnavailable):
        asyncio.run(collect(service))
    assert socket.closed and service._slots._value == 2
    service, socket, _ = make([], socket_type=SilentSocket)
    async def cancel():
        task = asyncio.create_task(collect(service))
        await asyncio.sleep(0)
        task.cancel()
        with pytest.raises(asyncio.CancelledError):
            await task
    asyncio.run(cancel())
    assert socket.closed and service._slots._value == 2


def test_waiting_for_capacity_is_bounded_without_connecting():
    service, _, calls = make([], mock_interview_provider_timeout_seconds=1)
    async def run():
        await service._slots.acquire()
        await service._slots.acquire()
        with pytest.raises(MockSpeechUnavailable):
            await collect(service)
        assert service._slots._value == 0
        service._slots.release()
        service._slots.release()
    asyncio.run(run())
    assert not calls


def test_replay_opens_independent_task_and_keeps_no_audio_cache():
    sockets = []
    def connect(*args, **kwargs):
        socket = Socket([event("task-started"), b"00", event("task-finished")])
        sockets.append(socket)
        return socket
    service, _, _ = make([])
    service._connector = connect
    async def run():
        for _ in range(20):
            assert await collect(service) == b"00"
    asyncio.run(run())
    assert all(s.closed for s in sockets) and service._slots._value == 2
    assert len({s.sent[0]["header"]["task_id"] for s in sockets}) == 20


@pytest.mark.parametrize("failure", [False, True])
def test_existing_runtime_audio_and_text_fallback_contract(monkeypatch, failure):
    events = [event("task-failed")] if failure else [event("task-started"), b"00", event("task-finished")]
    service, socket, _ = make(events)
    runtime = object.__new__(MockInterviewRuntime)
    runtime.repository = SimpleNamespace(duration_deadline=lambda _: None)
    runtime.tts = service
    runtime._meter = AsyncMock()
    messages = []
    async def send(value):
        messages.append(value)
    state = SimpleNamespace(phase="speaking", version=4, rounds=[SimpleNamespace(question_id="synthetic-q", question="合成提问")])
    controller = SimpleNamespace(closed=False, duration_ended=False, record={"data": {}}, has_audio=False, lock=asyncio.Lock(), send=send)
    monkeypatch.setattr("app.services.mock_interview_runtime.round_state", lambda _: state)
    asyncio.run(runtime._speak(controller, state))
    assert messages[0] == {"type": "audio_start", "questionId": "synthetic-q", "sampleRate": 24000}
    if failure:
        assert messages[-1]["type"] == "speech_unavailable" and "阅读题目" in messages[-1]["message"]
        runtime._meter.assert_awaited_once_with(controller, False)
    else:
        assert [m["type"] for m in messages] == ["audio_start", "audio", "audio_end"]
        assert base64.b64decode(messages[1]["pcm"]) == b"00" and controller.has_audio
        runtime._meter.assert_not_awaited()
    assert socket.closed and service._slots._value == 2


def test_global_legacy_protocol_and_voice_are_not_migrated():
    from test_mock_interview_tts import Socket as LegacySocket
    socket = LegacySocket([{"type": "session.updated"}, {"type": "response.audio.delta", "delta": "AAA="}, {"type": "session.finished"}])
    calls = []
    def connect(url, **kwargs):
        calls.append(url)
        return socket
    service = MockInterviewTts(Settings(_env_file=None, product_edition="global", chat_qwen_api_key="synthetic-key"), connector=connect)
    assert asyncio.run(collect(service)) == b"\0\0"
    assert calls == ["wss://dashscope-intl.aliyuncs.com/api-ws/v1/realtime?model=qwen3-tts-instruct-flash-realtime"]
    assert socket.sent[0]["session"]["voice"] == "Cherry" and socket.sent[0]["session"]["language_type"] == "English"


def test_runtime_end_during_audio_delivery_closes_provider_before_return(monkeypatch):
    service, socket, _ = make([event("task-started"), b"00", b"00", event("task-finished")])
    runtime = object.__new__(MockInterviewRuntime)
    runtime.repository = SimpleNamespace(duration_deadline=lambda _: None)
    runtime.tts = service
    state = SimpleNamespace(phase="speaking", version=4, rounds=[SimpleNamespace(question_id="synthetic-q", question="合成提问")])
    monkeypatch.setattr("app.services.mock_interview_runtime.round_state", lambda _: state)
    async def run():
        delivering = asyncio.Event()
        async def send(value):
            if value["type"] == "audio":
                delivering.set()
                await asyncio.Event().wait()
        controller = SimpleNamespace(closed=False, duration_ended=False, record={"data": {}}, has_audio=False, send=send)
        task = asyncio.create_task(runtime._speak(controller, state))
        await asyncio.wait_for(delivering.wait(), timeout=1)
        await runtime._cancel(task)
        assert task.cancelled()
        assert socket.closed and service._slots._value == 2
    asyncio.run(run())
