from __future__ import annotations

import json
import logging
import queue
import time

import pytest

from app.core.config import Settings
from app.deps import _configured_realtime_asr_gateway
from app.ports.realtime_speech import AudioFrame
from app.services.dashscope_realtime_asr_gateway import DashScopeRealtimeAsrGateway
from app.services.dashscope_task_asr_gateway import DashScopeTaskAsrGateway
from app.services.integration_verification import RealtimeAsrVerifier
from app.services.realtime_speech_service import NonRetryableAsrError, RetryableAsrError


class _TaskWebSocket:
    def __init__(self, *, fail_on_finish: bool = False, omit_finish: bool = False) -> None:
        self.events: queue.Queue[dict[str, object]] = queue.Queue()
        self.sent: list[str | bytes] = []
        self.closed = False
        self.current_task_id: str | None = None
        self.binary_count = 0
        self.fail_on_finish = fail_on_finish
        self.omit_finish = omit_finish

    def send(self, payload: str | bytes, opcode=None) -> None:  # noqa: ANN001
        del opcode
        self.sent.append(payload)
        if isinstance(payload, bytes):
            self.binary_count += 1
            if self.binary_count == 1 and self.current_task_id:
                self.events.put(_result_event(self.current_task_id, "流式部分", sentence_end=False))
            return
        message = json.loads(payload)
        action = message["header"]["action"]
        task_id = message["header"]["task_id"]
        if action == "run-task":
            self.current_task_id = task_id
            self.events.put({"header": {"event": "task-started", "task_id": task_id}, "payload": {}})
        elif action == "finish-task" and self.fail_on_finish:
            self.events.put({
                "header": {
                    "event": "task-failed",
                    "task_id": task_id,
                    "error_code": "Model.AccessDenied",
                    "error_message": "Model access denied.",
                },
                "payload": {},
            })
        elif action == "finish-task" and not self.omit_finish:
            self.events.put(_result_event(task_id, "流式部分已经完成。", sentence_end=True))
            self.events.put({"header": {"event": "task-finished", "task_id": task_id}, "payload": {}})

    def recv(self, timeout=None):  # noqa: ANN001
        try:
            return json.dumps(self.events.get(timeout=timeout or 1), ensure_ascii=False)
        except queue.Empty as exc:
            raise TimeoutError() from exc

    def settimeout(self, timeout) -> None:  # noqa: ANN001
        del timeout

    def close(self) -> None:
        self.closed = True


def _result_event(task_id: str, text: str, *, sentence_end: bool) -> dict[str, object]:
    return {
        "header": {"event": "result-generated", "task_id": task_id},
        "payload": {
            "output": {
                "sentence": {
                    "sentence_id": 1,
                    "text": text,
                    "sentence_end": sentence_end,
                    "heartbeat": False,
                }
            }
        },
    }


def _settings(**overrides) -> Settings:  # noqa: ANN003
    values = {
        "realtime_asr_api_key": "test-key",
        "realtime_asr_protocol": "qwen-audio-task",
        "realtime_asr_model": "qwen-audio-3.0-asr-flash-streaming",
        "realtime_asr_connect_timeout_seconds": 0.2,
        "realtime_asr_finalize_timeout_seconds": 0.2,
        **overrides,
    }
    return Settings(**values)


def _frame(
    *,
    source_kind: str = "microphone",
    revision: int = 1,
    is_final: bool = False,
    audio: bytes = b"audio",
) -> AudioFrame:
    now_ms = int(time.time() * 1000)
    return AudioFrame(
        publisher_id=f"publisher-{source_kind}",
        session_id="session-task",
        device_id="device-task",
        source_id=f"source-{source_kind}",
        source_kind=source_kind,  # type: ignore[arg-type]
        segment_id=f"segment-{source_kind}",
        revision=revision,
        sequence=revision,
        captured_at_ms=now_ms,
        started_at_ms=now_ms - 100,
        ended_at_ms=now_ms,
        duration_ms=100,
        codec="pcm-s16le",
        sample_rate_hz=16_000,
        channels=1,
        is_final=is_final,
        audio_bytes=audio,
    )


def test_task_gateway_streams_binary_partial_final_and_reuses_connection(monkeypatch) -> None:
    socket = _TaskWebSocket()
    monkeypatch.setattr("app.services.dashscope_task_asr_gateway.connect", lambda *args, **kwargs: socket)
    gateway = DashScopeTaskAsrGateway(_settings(), logging.getLogger("task-gateway"))
    partials: list[object] = []
    gateway.set_partial_listener(lambda _frame, result: partials.append(result))

    partial = gateway.transcribe(frame=_frame(audio=b"a" * 6_401), attempt=0)
    deadline = time.monotonic() + 0.2
    while not partials and time.monotonic() < deadline:
        time.sleep(0.005)
    final = gateway.finalize(frame=_frame(revision=2, is_final=True, audio=b"tail"), attempt=0)

    assert partial.text in {"", "流式部分"}
    assert [item.text for item in partials][:1] == ["流式部分"]
    assert final.text == "流式部分已经完成。"
    assert final.commit_sent_at_ms is not None
    assert final.completed_at_ms is not None
    assert final.connection_id == "microphone-task-1"
    assert len([item for item in socket.sent if isinstance(item, bytes)]) == 3
    control = [json.loads(item) for item in socket.sent if isinstance(item, str)]
    assert [item["header"]["action"] for item in control].count("run-task") == 2
    assert [item["header"]["action"] for item in control].count("finish-task") == 1
    assert control[0]["payload"]["model"] == "qwen-audio-3.0-asr-flash-streaming"
    assert control[0]["payload"]["parameters"]["max_sentence_silence"] == 400
    assert gateway.diagnostics("microphone")["task_finish_count"] == 1
    assert gateway.diagnostics("microphone")["final_count"] == 1
    gateway.close_session(session_id="session-task")


def test_task_gateway_failure_closes_only_affected_source(monkeypatch) -> None:
    system_socket = _TaskWebSocket()
    microphone_socket = _TaskWebSocket(fail_on_finish=True)
    sockets = iter([system_socket, microphone_socket])
    monkeypatch.setattr("app.services.dashscope_task_asr_gateway.connect", lambda *args, **kwargs: next(sockets))
    gateway = DashScopeTaskAsrGateway(_settings(), logging.getLogger("task-source-isolation"))
    gateway.warm_session(session_id="session-task", source_kind="system")

    with pytest.raises(NonRetryableAsrError, match="Model.AccessDenied"):
        gateway.finalize(frame=_frame(is_final=True), attempt=0)

    assert microphone_socket.closed is True
    assert system_socket.closed is False
    assert gateway.diagnostics("microphone")["active_provider_sessions"] == 0
    assert gateway.diagnostics("system")["active_provider_sessions"] == 1
    gateway.close_session(session_id="session-task")


def test_task_gateway_timeout_closes_ambiguous_source(monkeypatch) -> None:
    socket = _TaskWebSocket(omit_finish=True)
    monkeypatch.setattr("app.services.dashscope_task_asr_gateway.connect", lambda *args, **kwargs: socket)
    gateway = DashScopeTaskAsrGateway(
        _settings(realtime_asr_finalize_timeout_seconds=0.03),
        logging.getLogger("task-timeout"),
    )

    with pytest.raises(RetryableAsrError, match="realtime_asr_timeout"):
        gateway.finalize(frame=_frame(is_final=True), attempt=0)

    assert socket.closed is True
    assert gateway.diagnostics("microphone")["provider_timeout_count"] == 1
    assert gateway.diagnostics("microphone")["active_provider_sessions"] == 0


def test_task_gateway_suppresses_empty_results_and_keeps_diagnostics_content_free(monkeypatch) -> None:
    socket = _TaskWebSocket()
    monkeypatch.setattr("app.services.dashscope_task_asr_gateway.connect", lambda *args, **kwargs: socket)
    gateway = DashScopeTaskAsrGateway(_settings(), logging.getLogger("task-diagnostics"))
    gateway.warm_session(session_id="session-task", source_kind="microphone")
    task_id = socket.current_task_id
    assert task_id is not None
    socket.events.put(_result_event(task_id, "", sentence_end=False))
    time.sleep(0.02)

    diagnostics = gateway.diagnostics("microphone")
    runtime = gateway.runtime_status("microphone")
    assert diagnostics["blank_result_suppressed"] == 1
    assert runtime["protocol"] == "qwen-audio-task"
    assert runtime["model"] == "qwen-audio-3.0-asr-flash-streaming"
    assert not any(token in key.lower() for key in runtime for token in ("audio_bytes", "api_key", "transcript"))
    gateway.close_session(session_id="session-task")


def test_dependency_wiring_selects_new_and_legacy_protocols() -> None:
    new_gateway = _configured_realtime_asr_gateway(_settings(), logging.getLogger("new"))
    legacy_gateway = _configured_realtime_asr_gateway(
        Settings(realtime_asr_api_key="test", realtime_asr_protocol="qwen3-realtime"),
        logging.getLogger("legacy"),
    )

    assert isinstance(new_gateway, DashScopeTaskAsrGateway)
    assert isinstance(legacy_gateway, DashScopeRealtimeAsrGateway)
    with pytest.raises(RuntimeError, match="Unsupported realtime ASR protocol"):
        _configured_realtime_asr_gateway(
            Settings(realtime_asr_api_key="test", realtime_asr_protocol="unknown"),
            logging.getLogger("invalid"),
        )


def test_integration_verifier_uses_task_protocol_and_content_free_result(monkeypatch) -> None:
    socket = _TaskWebSocket()

    class _Abnf:
        OPCODE_BINARY = 2

    class _WebSocketModule:
        ABNF = _Abnf

        @staticmethod
        def create_connection(*_args, **_kwargs):  # noqa: ANN002, ANN003
            return socket

    verifier = RealtimeAsrVerifier()
    monkeypatch.setattr(verifier, "_audio_chunks_for_verification", lambda: ([b"synthetic-pcm"], "synthetic-test"))
    result = verifier._task_protocol_roundtrip(
        websocket=_WebSocketModule,
        settings=_settings(),
        ws_url="wss://dashscope.aliyuncs.com/api-ws/v1/inference",
        model_name="qwen-audio-3.0-asr-flash-streaming",
    )

    assert result["taskStarted"] is True
    assert result["taskFinished"] is True
    assert result["transcriptCharacters"] > 0
    assert "transcriptExcerpt" not in result
    assert any(isinstance(item, bytes) for item in socket.sent)
