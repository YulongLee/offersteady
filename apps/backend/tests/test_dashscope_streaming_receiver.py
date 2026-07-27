from __future__ import annotations

import json
import logging
import queue
import threading
import time

from app.core.config import Settings
from app.ports.realtime_speech import AudioFrame
from app.services.dashscope_realtime_asr_gateway import DashScopeRealtimeAsrGateway


class _StreamingFakeWebSocket:
    def __init__(self) -> None:
        self.sent: list[dict[str, object]] = []
        self.events: "queue.Queue[dict[str, object]]" = queue.Queue()
        self.events.put({"type": "session.created", "session": {"id": "streaming-session"}})
        self.closed = False

    def recv(self, timeout=None):  # noqa: ANN001
        try:
            return json.dumps(self.events.get(timeout=timeout or 1), ensure_ascii=False)
        except queue.Empty as exc:
            raise TimeoutError() from exc

    def send(self, payload: str) -> None:
        message = json.loads(payload)
        self.sent.append(message)
        if message["type"] == "input_audio_buffer.append":
            threading.Timer(
                0.01,
                lambda: self.events.put({
                    "type": "conversation.item.input_audio_transcription.text",
                    "text": "持续流式识别",
                }),
            ).start()
        if message["type"] == "input_audio_buffer.commit":
            threading.Timer(
                0.01,
                lambda: self.events.put({
                    "type": "conversation.item.input_audio_transcription.completed",
                    "transcript": "持续流式识别完成",
                }),
            ).start()

    def close(self) -> None:
        self.closed = True


def _frame(*, revision: int, is_final: bool, audio: bytes) -> AudioFrame:
    return AudioFrame(
        publisher_id="publisher-stream",
        session_id="session-stream",
        device_id="device-stream",
        source_id="mic-stream",
        source_kind="microphone",
        segment_id="segment-stream",
        revision=revision,
        sequence=revision,
        captured_at_ms=int(time.time() * 1000),
        started_at_ms=1,
        ended_at_ms=revision * 100,
        duration_ms=100,
        codec="pcm-s16le",
        sample_rate_hz=16000,
        channels=1,
        is_final=is_final,
        audio_bytes=audio,
    )


def test_gateway_receives_partial_on_background_pump_and_reuses_connection(monkeypatch) -> None:
    socket = _StreamingFakeWebSocket()
    monkeypatch.setattr(
        "app.services.dashscope_realtime_asr_gateway.connect",
        lambda *args, **kwargs: socket,
    )
    gateway = DashScopeRealtimeAsrGateway(
        Settings(
            realtime_asr_api_key="test-key",
            realtime_asr_partial_timeout_seconds=0.2,
            realtime_asr_finalize_timeout_seconds=0.5,
        ),
        logging.getLogger("test-streaming-receiver"),
    )

    partial = gateway.transcribe(frame=_frame(revision=1, is_final=False, audio=b"partial"), attempt=0)
    final = gateway.transcribe(frame=_frame(revision=2, is_final=True, audio=b"tail"), attempt=0)

    assert partial.text == "持续流式识别"
    assert final.text == "持续流式识别完成"
    assert gateway.diagnostics("microphone")["connection_recreations"] == 1
    assert [item["type"] for item in socket.sent].count("input_audio_buffer.commit") == 1
    gateway._close_source_session("session-stream:microphone")


def test_gateway_delivers_partial_that_arrives_between_audio_frames(monkeypatch) -> None:
    socket = _StreamingFakeWebSocket()
    monkeypatch.setattr(
        "app.services.dashscope_realtime_asr_gateway.connect",
        lambda *args, **kwargs: socket,
    )
    gateway = DashScopeRealtimeAsrGateway(
        Settings(
            realtime_asr_api_key="test-key",
            realtime_asr_partial_timeout_seconds=0.001,
            realtime_asr_finalize_timeout_seconds=0.5,
        ),
        logging.getLogger("test-between-frame-partial"),
    )

    first = gateway.transcribe(frame=_frame(revision=1, is_final=False, audio=b"first"), attempt=0)
    assert first.text == ""
    time.sleep(0.03)
    second = gateway.transcribe(frame=_frame(revision=2, is_final=False, audio=b"second"), attempt=0)

    assert second.text == "持续流式识别"
    gateway._close_source_session("session-stream:microphone")
