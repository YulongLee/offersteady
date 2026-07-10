from __future__ import annotations

import base64
import json
import logging
import threading
import time
from dataclasses import dataclass, field, replace
from urllib.parse import urlencode

from websockets.sync.client import connect

from app.core.config import Settings
from app.ports.realtime_speech import AsrUsageReport, AudioFrame, RealtimeAsrGatewayPort, TranscriptResult
from app.services.realtime_speech_service import NonRetryableAsrError, RetryableAsrError


@dataclass
class _SourceRealtimeSession:
    connection: object
    sample_rate_hz: int
    created_at_monotonic: float
    updated_at_monotonic: float
    source_session_key: str
    source_kind: str
    current_segment_id: str | None = None
    transcript_text: str = ""
    mode: str = "manual"
    lock: threading.Lock = field(default_factory=threading.Lock)


class DashScopeRealtimeAsrGateway(RealtimeAsrGatewayPort):
    def __init__(self, settings: Settings, logger: logging.Logger) -> None:
        self.settings = settings
        self.logger = logger
        self._source_sessions: dict[str, _SourceRealtimeSession] = {}
        self._source_sessions_lock = threading.Lock()
        self._connection_recreations: dict[str, int] = {}
        self._session_created_missing: dict[str, int] = {}
        self._session_update_failures: dict[str, int] = {}
        self._completed_missing: dict[str, int] = {}
        self._blank_partial_suppressed: dict[str, int] = {}
        self._vad_to_manual_fallbacks: dict[str, int] = {}
        self._mode_by_source: dict[str, str] = {}
        self._connection_state_by_source: dict[str, str] = {}
        self._last_error_by_source: dict[str, str] = {}

    @staticmethod
    def _normalize_audio_codec(codec: str) -> str:
        normalized = (codec or "").strip().lower().replace("_", "-")
        if normalized in {"pcm", "pcm-s16le", "audio/pcm", "audio/raw", "raw"}:
            return "pcm-s16le"
        return normalized

    def transcribe(self, *, frame: AudioFrame, attempt: int) -> TranscriptResult:
        if not self.settings.realtime_asr_api_key:
            raise NonRetryableAsrError("realtime_asr_api_key_missing")
        normalized_codec = self._normalize_audio_codec(frame.codec)
        if normalized_codec != "pcm-s16le":
            raise NonRetryableAsrError("unsupported_audio_codec")
        if frame.codec != normalized_codec:
            self.logger.warning(
                "normalize_realtime_asr_codec",
                extra={"from": frame.codec, "to": normalized_codec, "sessionId": frame.session_id},
            )
        if frame.sample_rate_hz <= 0 or frame.channels <= 0:
            raise NonRetryableAsrError("invalid_audio_metadata")
        normalized_frame = frame
        if frame.codec != normalized_codec:
            normalized_frame = replace(frame, codec=normalized_codec)
        text, first_text_at_ms, completed_at_ms = self._roundtrip(normalized_frame)
        cleaned = text.strip()
        return TranscriptResult(
            text=cleaned,
            confidence=0.96 if frame.is_final else 0.82,
            overlap=False,
            usage=AsrUsageReport(
                total_tokens=max(1, len(cleaned) // 2),
                provider_name=self.settings.realtime_asr_provider,
                model_name=self.settings.realtime_asr_model,
            ),
            first_text_at_ms=first_text_at_ms,
            completed_at_ms=completed_at_ms,
        )

    def diagnostics(self, source_kind: str) -> dict[str, int]:
        return {
            "connection_recreations": self._connection_recreations.get(source_kind, 0),
            "session_created_missing": self._session_created_missing.get(source_kind, 0),
            "session_update_failures": self._session_update_failures.get(source_kind, 0),
            "completed_missing": self._completed_missing.get(source_kind, 0),
            "blank_partial_suppressed": self._blank_partial_suppressed.get(source_kind, 0),
            "vad_to_manual_fallbacks": self._vad_to_manual_fallbacks.get(source_kind, 0),
        }

    def runtime_status(self, source_kind: str) -> dict[str, str | int | None]:
        return {
            "mode": self._mode_by_source.get(source_kind),
            "connection_state": self._connection_state_by_source.get(source_kind),
            "last_error_code": self._last_error_by_source.get(source_kind),
            **self.diagnostics(source_kind),
        }

    def _roundtrip(self, frame: AudioFrame) -> tuple[str, int | None, int | None]:
        session = self._get_or_create_source_session(frame)
        try:
            with session.lock:
                self._prepare_segment_state(session, frame)
                if frame.audio_bytes:
                    self._send_audio_chunks(session.connection, frame.audio_bytes)
                    session.updated_at_monotonic = time.monotonic()
                transcript_text, transcript_events, first_text_at_ms, completed_at_ms = self._drain_events(
                    session.connection,
                    frame=frame,
                    finalize=False,
                    previous_text=session.transcript_text,
                    source_kind=session.source_kind,
                )
                if frame.is_final:
                    final_text = transcript_text
                    final_events = 0
                    final_first_text_at_ms = None
                    final_completed_at_ms = completed_at_ms
                    if completed_at_ms is None:
                        session.connection.send(json.dumps({
                            "event_id": f"rt-commit-{frame.segment_id}-{frame.revision}",
                            "type": "input_audio_buffer.commit",
                        }))
                        final_text, final_events, final_first_text_at_ms, final_completed_at_ms = self._drain_events(
                            session.connection,
                            frame=frame,
                            finalize=True,
                            previous_text=transcript_text,
                            source_kind=session.source_kind,
                        )
                    session.transcript_text = final_text
                    session.current_segment_id = None
                    session.transcript_text = ""
                    transcript_text = final_text
                    transcript_events += final_events
                    first_text_at_ms = first_text_at_ms or final_first_text_at_ms
                    completed_at_ms = final_completed_at_ms or completed_at_ms
                else:
                    session.transcript_text = transcript_text
                self._connection_state_by_source[session.source_kind] = "receiving"
                self._last_error_by_source.pop(session.source_kind, None)
                return transcript_text, first_text_at_ms, completed_at_ms
        except TimeoutError as exc:
            self._record_error(frame.source_kind, "realtime_asr_timeout")
            self._close_source_session(self._source_session_key(frame))
            raise RetryableAsrError("realtime_asr_timeout") from exc
        except OSError as exc:
            self._record_error(frame.source_kind, "realtime_asr_connection_failed")
            self._close_source_session(self._source_session_key(frame))
            raise RetryableAsrError("realtime_asr_connection_failed") from exc
        except json.JSONDecodeError as exc:
            self._record_error(frame.source_kind, "realtime_asr_invalid_response")
            self._close_source_session(self._source_session_key(frame))
            raise NonRetryableAsrError("realtime_asr_invalid_response") from exc

    def _source_session_key(self, frame: AudioFrame) -> str:
        return f"{frame.session_id}:{frame.source_kind}"

    def _prepare_segment_state(self, session: _SourceRealtimeSession, frame: AudioFrame) -> None:
        if session.current_segment_id == frame.segment_id:
            return
        session.current_segment_id = frame.segment_id
        session.transcript_text = ""

    def _get_or_create_source_session(self, frame: AudioFrame) -> _SourceRealtimeSession:
        key = self._source_session_key(frame)
        with self._source_sessions_lock:
            self._sweep_stale_sessions_locked()
            existing = self._source_sessions.get(key)
            if existing is not None:
                existing.updated_at_monotonic = time.monotonic()
                return existing
            connection, mode = self._open_connection(frame)
            self._connection_recreations[frame.source_kind] = self._connection_recreations.get(frame.source_kind, 0) + 1
            session = _SourceRealtimeSession(
                connection=connection,
                sample_rate_hz=frame.sample_rate_hz,
                created_at_monotonic=time.monotonic(),
                updated_at_monotonic=time.monotonic(),
                source_session_key=key,
                source_kind=frame.source_kind,
                mode=mode,
            )
            self._source_sessions[key] = session
            self._mode_by_source[frame.source_kind] = mode
            self._connection_state_by_source[frame.source_kind] = "ready"
            return session

    def _open_connection(self, frame: AudioFrame) -> tuple[object, str]:
        connect_url = self._connect_url()
        headers = {
            "Authorization": f"Bearer {self.settings.realtime_asr_api_key}",
            "OpenAI-Beta": "realtime=v1",
        }
        websocket = connect(
            connect_url,
            additional_headers=headers,
            open_timeout=min(
                self.settings.realtime_asr_connect_timeout_seconds,
                self.settings.integration_http_timeout_seconds,
            ),
            close_timeout=min(
                self.settings.realtime_asr_connect_timeout_seconds,
                self.settings.integration_http_timeout_seconds,
            ),
            max_size=2_097_152,
            logger=self.logger,
        )
        first_event = json.loads(
            websocket.recv(
                timeout=min(
                    self.settings.realtime_asr_connect_timeout_seconds,
                    self.settings.integration_http_timeout_seconds,
                )
            )
        )
        if first_event.get("type") == "error":
            websocket.close()
            self._record_error(frame.source_kind, self._error_message(first_event))
            raise NonRetryableAsrError(self._error_message(first_event))
        if first_event.get("type") != "session.created":
            websocket.close()
            self._session_created_missing[frame.source_kind] = self._session_created_missing.get(frame.source_kind, 0) + 1
            self._record_error(frame.source_kind, "realtime_asr_session_created_missing")
            raise RetryableAsrError("realtime_asr_session_created_missing")
        session_payload, mode = self._session_update_payload(frame)
        try:
            websocket.send(json.dumps({
                "event_id": f"rt-session-{frame.segment_id}-{frame.revision}",
                "type": "session.update",
                "session": session_payload,
            }))
        except OSError as exc:
            self._session_update_failures[frame.source_kind] = self._session_update_failures.get(frame.source_kind, 0) + 1
            self._record_error(frame.source_kind, "realtime_asr_session_update_failed")
            websocket.close()
            raise RetryableAsrError("realtime_asr_session_update_failed") from exc
        return websocket, mode

    def _session_update_payload(self, frame: AudioFrame) -> tuple[dict[str, object], str]:
        requested_mode = (self.settings.realtime_asr_turn_detection_mode or "manual").strip().lower()
        mode = "vad" if requested_mode in {"vad", "server_vad", "server-vad"} else "manual"
        payload: dict[str, object] = {
            "modalities": ["text"],
            "input_audio_format": "pcm",
            "sample_rate": frame.sample_rate_hz,
            "input_audio_transcription": {
                "language": "zh",
            },
        }
        if mode == "vad":
            payload["turn_detection"] = {
                "type": "server_vad",
                "threshold": self.settings.realtime_asr_turn_detection_threshold,
                "silence_duration_ms": self.settings.realtime_asr_turn_detection_silence_duration_ms,
            }
        else:
            payload["turn_detection"] = None
        return payload, mode

    def _drain_events(self, websocket, *, frame: AudioFrame, finalize: bool, previous_text: str, source_kind: str) -> tuple[str, int, int | None, int | None]:
        transcript_text = previous_text
        transcript_events = 0
        first_text_at_ms: int | None = None
        completed_at_ms: int | None = None
        wait_seconds = (
            self.settings.realtime_asr_finalize_timeout_seconds
            if finalize
            else self.settings.realtime_asr_partial_timeout_seconds
        )
        deadline = time.monotonic() + max(0.006, wait_seconds)
        completed = False
        while time.monotonic() < deadline:
            timeout = max(0.006, deadline - time.monotonic())
            try:
                raw = websocket.recv(timeout=timeout)
            except TimeoutError:
                break
            message = json.loads(raw)
            event_type = message.get("type")
            if event_type == "error":
                raise NonRetryableAsrError(self._error_message(message))
            if event_type == "session.updated":
                continue
            if event_type in {"conversation.item.input_audio_transcription.text", "conversation.item.input_audio_transcription.completed"}:
                transcript_events += 1
                next_text = (
                    message.get("transcript")
                    or message.get("text")
                    or message.get("stash")
                    or transcript_text
                )
                if isinstance(next_text, str) and next_text.strip():
                    transcript_text = next_text
                    if first_text_at_ms is None:
                        first_text_at_ms = int(time.time() * 1000)
                elif event_type == "conversation.item.input_audio_transcription.text":
                    self._blank_partial_suppressed[source_kind] = self._blank_partial_suppressed.get(source_kind, 0) + 1
            if event_type == "conversation.item.input_audio_transcription.completed":
                completed = True
                completed_at_ms = int(time.time() * 1000)
                break
        if finalize and not completed and not transcript_text.strip():
            self._completed_missing[source_kind] = self._completed_missing.get(source_kind, 0) + 1
            raise RetryableAsrError("realtime_asr_transcript_missing")
        if finalize and not completed and transcript_text.strip():
            self._connection_state_by_source[source_kind] = "partial"
            self._last_error_by_source.pop(source_kind, None)
            completed_at_ms = int(time.time() * 1000)
        return transcript_text, transcript_events, first_text_at_ms, completed_at_ms

    def _close_source_session(self, source_session_key: str) -> None:
        with self._source_sessions_lock:
            session = self._source_sessions.pop(source_session_key, None)
        if session is None:
            return
        self._connection_state_by_source[session.source_kind] = "closed"
        try:
            session.connection.close()
        except Exception:
            pass

    def _sweep_stale_sessions_locked(self) -> None:
        now = time.monotonic()
        stale_session_keys = [
            source_session_key
            for source_session_key, session in self._source_sessions.items()
            if now - session.updated_at_monotonic > 8
        ]
        for source_session_key in stale_session_keys:
            session = self._source_sessions.pop(source_session_key, None)
            if session is None:
                continue
            try:
                session.connection.close()
            except Exception:
                pass

    def _connect_url(self) -> str:
        dedicated_workspace_base = None
        if self.settings.realtime_asr_workspace_id:
            dedicated_workspace_base = (
                f"wss://{self.settings.realtime_asr_workspace_id}."
                f"{self.settings.realtime_asr_workspace_region}.maas.aliyuncs.com/api-ws/v1/realtime"
            )
        base = dedicated_workspace_base or self.settings.realtime_asr_ws_url or self.settings.realtime_asr_base_url or "wss://dashscope.aliyuncs.com/api-ws/v1/realtime"
        if "model=" in base:
            return base
        separator = "&" if "?" in base else "?"
        return f"{base}{separator}{urlencode({'model': self.settings.realtime_asr_model})}"

    def _record_error(self, source_kind: str, code: str) -> None:
        self._connection_state_by_source[source_kind] = "error"
        self._last_error_by_source[source_kind] = code

    @staticmethod
    def _send_audio_chunks(websocket, audio_bytes: bytes) -> None:
        if not audio_bytes:
            return
        for index in range(0, len(audio_bytes), 1600):
            chunk = audio_bytes[index : index + 1600]
            websocket.send(json.dumps({
                "event_id": f"rt-audio-{index}",
                "type": "input_audio_buffer.append",
                "audio": base64.b64encode(chunk).decode("ascii"),
            }))

    @staticmethod
    def _error_message(payload: dict[str, object]) -> str:
        error = payload.get("error")
        if isinstance(error, dict):
            message = error.get("message")
            if isinstance(message, str) and message.strip():
                return message.strip()
        message = payload.get("message")
        if isinstance(message, str) and message.strip():
            return message.strip()
        return "realtime_asr_error"
