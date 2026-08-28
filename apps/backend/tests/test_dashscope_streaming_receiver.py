from __future__ import annotations

import base64
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


class _LatePartialAfterCompletedFakeWebSocket(_StreamingFakeWebSocket):
    def send(self, payload: str) -> None:
        message = json.loads(payload)
        self.sent.append(message)
        if message["type"] == "input_audio_buffer.append":
            return
        if message["type"] == "input_audio_buffer.commit":
            self.events.put({
                "type": "conversation.item.input_audio_transcription.completed",
                "transcript": "最终识别结果",
            })
            self.events.put({
                "type": "conversation.item.input_audio_transcription.text",
                "text": "迟到的不完整识别",
            })


class _PartialAfterTwoAppendsFakeWebSocket(_StreamingFakeWebSocket):
    def __init__(self) -> None:
        super().__init__()
        self.append_count = 0

    def send(self, payload: str) -> None:
        message = json.loads(payload)
        self.sent.append(message)
        if message["type"] != "input_audio_buffer.append":
            return
        self.append_count += 1
        if self.append_count == 2:
            threading.Timer(
                0.01,
                lambda: self.events.put({
                    "type": "conversation.item.input_audio_transcription.text",
                    "text": "第二帧后返回首字",
                }),
            ).start()


class _RevisionPerAppendFakeWebSocket(_StreamingFakeWebSocket):
    def __init__(self) -> None:
        super().__init__()
        self.append_count = 0

    def send(self, payload: str) -> None:
        message = json.loads(payload)
        self.sent.append(message)
        if message["type"] != "input_audio_buffer.append":
            return
        self.append_count += 1
        revision = self.append_count
        threading.Timer(
            0.005,
            lambda: self.events.put({
                "type": "conversation.item.input_audio_transcription.text",
                "text": f"持续流式识别第{revision}版",
            }),
        ).start()


class _PostCommitPartialFakeWebSocket(_StreamingFakeWebSocket):
    def send(self, payload: str) -> None:
        message = json.loads(payload)
        self.sent.append(message)
        if message["type"] != "input_audio_buffer.commit":
            return
        self.events.put({
            "type": "conversation.item.input_audio_transcription.text",
            "text": "提交后补齐尾词",
        })
        threading.Timer(
            0.01,
            lambda: self.events.put({
                "type": "conversation.item.input_audio_transcription.completed",
                "transcript": "提交后补齐尾词完成",
            }),
        ).start()


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
            realtime_asr_nonblocking_partials_enabled=False,
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
    delivered_partials: list[tuple[AudioFrame, object]] = []
    delivered = threading.Event()
    gateway.set_partial_listener(lambda frame, result: (delivered_partials.append((frame, result)), delivered.set()))

    first = gateway.transcribe(frame=_frame(revision=1, is_final=False, audio=b"first"), attempt=0)
    assert first.text == ""
    assert delivered.wait(timeout=0.2)
    second = gateway.transcribe(frame=_frame(revision=2, is_final=False, audio=b"second"), attempt=0)

    assert len(delivered_partials) == 1
    assert delivered_partials[0][0].revision == 1
    assert delivered_partials[0][1].text == "持续流式识别"
    assert delivered_partials[0][1].partial_received_at_ms is not None
    # The next append must not re-publish the provider revision already emitted
    # by the receive loop.
    assert second.text == ""
    gateway._close_source_session("session-stream:microphone")


def test_gateway_preserves_first_append_timestamp_until_first_partial(monkeypatch) -> None:
    socket = _PartialAfterTwoAppendsFakeWebSocket()
    monkeypatch.setattr(
        "app.services.dashscope_realtime_asr_gateway.connect",
        lambda *args, **kwargs: socket,
    )
    gateway = DashScopeRealtimeAsrGateway(
        Settings(
            realtime_asr_api_key="test-key",
            realtime_asr_nonblocking_partials_enabled=True,
        ),
        logging.getLogger("test-first-append-anchor"),
    )
    delivered_partials: list[object] = []
    delivered = threading.Event()
    gateway.set_partial_listener(lambda _frame, result: (delivered_partials.append(result), delivered.set()))

    first = gateway.transcribe(frame=_frame(revision=1, is_final=False, audio=b"first"), attempt=0)
    time.sleep(0.01)
    second = gateway.transcribe(frame=_frame(revision=2, is_final=False, audio=b"second"), attempt=0)

    assert first.first_audio_appended_at_ms == first.audio_appended_at_ms
    assert second.first_audio_appended_at_ms == first.audio_appended_at_ms
    assert second.audio_appended_at_ms is not None
    assert first.audio_appended_at_ms is not None
    assert second.audio_appended_at_ms > first.audio_appended_at_ms
    assert delivered.wait(timeout=0.2)
    partial = delivered_partials[0]
    assert partial.first_audio_appended_at_ms == first.audio_appended_at_ms
    assert partial.audio_appended_at_ms == second.audio_appended_at_ms
    gateway._close_source_session("session-stream:microphone")


def test_gateway_delivers_each_unseen_provider_revision_before_commit(monkeypatch) -> None:
    socket = _RevisionPerAppendFakeWebSocket()
    monkeypatch.setattr(
        "app.services.dashscope_realtime_asr_gateway.connect",
        lambda *args, **kwargs: socket,
    )
    gateway = DashScopeRealtimeAsrGateway(
        Settings(
            realtime_asr_api_key="test-key",
            realtime_asr_nonblocking_partials_enabled=True,
        ),
        logging.getLogger("test-continuous-partial-revisions"),
    )
    delivered_partials: list[object] = []
    delivered = threading.Event()

    def observe(_frame, result) -> None:  # noqa: ANN001
        delivered_partials.append(result)
        if len(delivered_partials) == 2:
            delivered.set()

    gateway.set_partial_listener(observe)
    gateway.transcribe(frame=_frame(revision=1, is_final=False, audio=b"first"), attempt=0)
    time.sleep(0.02)
    gateway.transcribe(frame=_frame(revision=2, is_final=False, audio=b"second"), attempt=0)

    assert delivered.wait(timeout=0.2)
    assert [item.text for item in delivered_partials] == [
        "持续流式识别第1版",
        "持续流式识别第2版",
    ]
    assert [item.provider_revision for item in delivered_partials] == sorted(
        item.provider_revision for item in delivered_partials
    )
    assert all(item.completed_at_ms is None for item in delivered_partials)
    assert not any(message["type"] == "input_audio_buffer.commit" for message in socket.sent)
    gateway._close_source_session("session-stream:microphone")


def test_gateway_delivers_post_commit_partial_before_authoritative_final(monkeypatch) -> None:
    socket = _PostCommitPartialFakeWebSocket()
    monkeypatch.setattr("app.services.dashscope_realtime_asr_gateway.connect", lambda *args, **kwargs: socket)
    gateway = DashScopeRealtimeAsrGateway(
        Settings(realtime_asr_api_key="test-key", realtime_asr_finalize_timeout_seconds=0.5),
        logging.getLogger("test-post-commit-partial"),
    )
    delivered: list[object] = []
    gateway.set_partial_listener(lambda _frame, result: delivered.append(result))

    final = gateway.transcribe(frame=_frame(revision=1, is_final=True, audio=b"tail"), attempt=0)

    assert [item.text for item in delivered] == ["提交后补齐尾词"]
    assert final.text == "提交后补齐尾词完成"
    assert final.commit_sent_at_ms is not None
    assert final.partial_received_at_ms is not None
    assert final.partial_received_at_ms >= final.commit_sent_at_ms
    gateway._close_source_session("session-stream:microphone")


def test_gateway_commit_silence_experiment_is_disabled_by_default_and_bounded(monkeypatch) -> None:
    default_socket = _StreamingFakeWebSocket()
    sockets = iter([default_socket, _StreamingFakeWebSocket()])
    monkeypatch.setattr("app.services.dashscope_realtime_asr_gateway.connect", lambda *args, **kwargs: next(sockets))
    default_gateway = DashScopeRealtimeAsrGateway(
        Settings(realtime_asr_api_key="test-key", realtime_asr_finalize_timeout_seconds=0.5),
        logging.getLogger("test-default-commit-flush"),
    )
    default_gateway.transcribe(frame=_frame(revision=1, is_final=True, audio=b"tail"), attempt=0)
    assert [item["type"] for item in default_socket.sent].count("input_audio_buffer.append") == 1
    default_gateway._close_source_session("session-stream:microphone")

    enabled_socket = next(iter([_StreamingFakeWebSocket()]))
    monkeypatch.setattr("app.services.dashscope_realtime_asr_gateway.connect", lambda *args, **kwargs: enabled_socket)
    enabled_gateway = DashScopeRealtimeAsrGateway(
        Settings(
            realtime_asr_api_key="test-key",
            realtime_asr_finalize_timeout_seconds=0.5,
            realtime_asr_commit_silence_ms=100,
        ),
        logging.getLogger("test-enabled-commit-flush"),
    )
    enabled_gateway.transcribe(frame=_frame(revision=1, is_final=True, audio=b"tail"), attempt=0)
    appends = [item for item in enabled_socket.sent if item["type"] == "input_audio_buffer.append"]
    assert len(appends) == 2
    assert len(base64.b64decode(str(appends[-1]["audio"]))) == 3_200
    assert set(base64.b64decode(str(appends[-1]["audio"]))) == {0}
    enabled_gateway._close_source_session("session-stream:microphone")


def test_gateway_does_not_wait_for_provider_partial_after_audio_append(monkeypatch) -> None:
    socket = _StreamingFakeWebSocket()
    monkeypatch.setattr(
        "app.services.dashscope_realtime_asr_gateway.connect",
        lambda *args, **kwargs: socket,
    )
    gateway = DashScopeRealtimeAsrGateway(
        Settings(
            realtime_asr_api_key="test-key",
            realtime_asr_partial_timeout_seconds=0.5,
            realtime_asr_finalize_timeout_seconds=0.5,
            realtime_asr_nonblocking_partials_enabled=True,
        ),
        logging.getLogger("test-nonblocking-partial"),
    )

    started_at = time.monotonic()
    partial = gateway.transcribe(frame=_frame(revision=1, is_final=False, audio=b"partial"), attempt=0)
    elapsed = time.monotonic() - started_at

    assert partial.text == ""
    assert elapsed < 0.1
    time.sleep(0.03)
    delivered = gateway.transcribe(frame=_frame(revision=2, is_final=False, audio=b"next"), attempt=0)
    assert delivered.text == "持续流式识别"
    gateway._close_source_session("session-stream:microphone")


def test_gateway_freezes_completed_transcript_and_ignores_late_partial(monkeypatch) -> None:
    socket = _LatePartialAfterCompletedFakeWebSocket()
    monkeypatch.setattr(
        "app.services.dashscope_realtime_asr_gateway.connect",
        lambda *args, **kwargs: socket,
    )
    gateway = DashScopeRealtimeAsrGateway(
        Settings(
            realtime_asr_api_key="test-key",
            realtime_asr_finalize_timeout_seconds=0.5,
        ),
        logging.getLogger("test-late-partial-after-completed"),
    )

    final = gateway.transcribe(frame=_frame(revision=1, is_final=True, audio=b"final"), attempt=0)

    assert final.text == "最终识别结果"
    gateway._close_source_session("session-stream:microphone")
