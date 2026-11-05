import asyncio
import base64
import json

import pytest
from websockets.exceptions import ConnectionClosedError
from websockets.frames import Close

from app.core.config import Settings
from app.services.mock_interview_tts import MockInterviewTts, MockSpeechUnavailable


class Socket:
    def __init__(self, events):
        self.events = iter(events)
        self.sent = []
        self.closed = False

    async def __aenter__(self):
        return self

    async def __aexit__(self, *args):
        self.closed = True

    async def send(self, message):
        self.sent.append(json.loads(message))

    def __aiter__(self):
        return self

    async def __anext__(self):
        event = next(self.events, None)
        if event is None:
            raise StopAsyncIteration
        return json.dumps(event)


def make(events):
    socket = Socket(events)
    service = MockInterviewTts(Settings(_env_file=None, chat_qwen_api_key="synthetic-key"), connector=lambda *a, **kw: socket)
    return service, socket


def test_stream_uses_tts_commit_protocol_and_closes():
    service, socket = make([
        {"type": "session.created"}, {"type": "session.updated"},
        {"type": "response.audio.delta", "delta": base64.b64encode(b"\0\0\1\0").decode()},
        {"type": "response.done", "response": {"status": "completed"}},
        {"type": "session.finished"},
    ])
    async def run():
        return b"".join([chunk async for chunk in service.stream("请介绍一个合成项目。")])
    assert asyncio.run(run()) == b"\0\0\1\0"
    assert [e["type"] for e in socket.sent] == ["session.update", "input_text_buffer.append", "input_text_buffer.commit", "session.finish"]
    assert socket.sent[0]["session"]["sample_rate"] == 24000
    assert len({e["event_id"] for e in socket.sent}) == 4
    assert socket.closed


@pytest.mark.parametrize("events", [
    [{"type": "error", "message": "secret-provider-payload"}],
    [{"type": "session.updated"}, {"type": "session.finished"}],
    [{"type": "session.updated"}, {"type": "response.audio.delta", "delta": "!bad!"}],
    [{"type": "session.updated"}],
])
def test_failure_is_explicit_redacted_and_closed(events):
    service, socket = make(events)
    async def run():
        return [chunk async for chunk in service.stream("合成测试")]
    with pytest.raises(MockSpeechUnavailable) as error:
        asyncio.run(run())
    assert "secret-provider-payload" not in str(error.value)
    assert socket.closed


def test_buffer_limit_and_early_cancel_close_resources():
    events = [{"type": "session.updated"}] + [{"type": "response.audio.delta", "delta": "AAAA"}] * 3
    service, socket = make(events)
    service.max_audio_bytes = 2
    async def overflow():
        return [chunk async for chunk in service.stream("测试")]
    with pytest.raises(MockSpeechUnavailable):
        asyncio.run(overflow())
    assert socket.closed
    service, socket = make(events)
    async def cancelled():
        stream = service.stream("测试")
        assert await anext(stream)
        await stream.aclose()
    asyncio.run(cancelled())
    assert socket.closed
    assert service._slots._value == service.settings.mock_interview_provider_concurrency


def test_access_denied_is_actionable_and_does_not_expose_credentials():
    class DeniedSocket(Socket):
        async def __anext__(self):
            raise ConnectionClosedError(Close(1007, "Model access denied."), None)
    socket = DeniedSocket([])
    service = MockInterviewTts(Settings(_env_file=None, chat_qwen_api_key="synthetic-key"), connector=lambda *a, **kw: socket)
    async def run():
        return [chunk async for chunk in service.stream("合成测试")]
    with pytest.raises(MockSpeechUnavailable, match="未获此语音模型调用权限") as error:
        asyncio.run(run())
    assert "synthetic-key" not in str(error.value)
    assert socket.closed


def test_provider_timeout_closes_and_releases_capacity():
    class SilentSocket(Socket):
        async def __anext__(self):
            await asyncio.sleep(10)
            return json.dumps({"type": "session.created"})
    socket = SilentSocket([])
    service = MockInterviewTts(Settings(_env_file=None, chat_qwen_api_key="synthetic-key",
        mock_interview_provider_timeout_seconds=1), connector=lambda *a, **kw: socket)
    async def run():
        return [chunk async for chunk in service.stream("合成测试")]
    with pytest.raises(MockSpeechUnavailable):
        asyncio.run(run())
    assert socket.closed
    assert service._slots._value == service.settings.mock_interview_provider_concurrency
