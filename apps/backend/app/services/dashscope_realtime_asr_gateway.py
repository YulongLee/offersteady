from __future__ import annotations

import base64
import json
import logging
import threading
import time
from dataclasses import dataclass, field, replace
from typing import Callable
from urllib.parse import urlencode

from websockets.sync.client import connect

from app.core.config import Settings
from app.ports.interview_session import InterviewLanguage
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
    interview_language: InterviewLanguage = "zh-CN"
    connection_id: str = "unknown"
    source_generation: int = 1
    current_segment_id: str | None = None
    transcript_text: str = ""
    mode: str = "manual"
    lock: threading.Lock = field(default_factory=threading.Lock)
    event_condition: threading.Condition = field(default_factory=threading.Condition)
    event_revision: int = 0
    delivered_revision: int = 0
    first_text_at_ms: int | None = None
    latest_text_at_ms: int | None = None
    completed_at_ms: int | None = None
    receiver_error: Exception | None = None
    accepting_transcript_events: bool = True
    closed: bool = False
    receiver_thread: threading.Thread | None = None
    latest_frame: AudioFrame | None = None
    latest_audio_appended_at_ms: int | None = None
    first_audio_appended_at_ms: int | None = None
    first_partial_observed_for_segment: bool = False
    latest_asr_lock_wait_start_at_ms: int | None = None
    latest_asr_lock_acquired_at_ms: int | None = None
    latest_qwen_send_enqueue_at_ms: int | None = None
    latest_qwen_ws_send_start_at_ms: int | None = None
    latest_qwen_ws_send_complete_at_ms: int | None = None


class DashScopeRealtimeAsrGateway(RealtimeAsrGatewayPort):
    def __init__(self, settings: Settings, logger: logging.Logger) -> None:
        self.settings = settings
        self.logger = logger
        self._source_sessions: dict[str, _SourceRealtimeSession] = {}
        self._source_sessions_lock = threading.Lock()
        self._connection_recreations: dict[str, int] = {}
        self._connection_create_counts: dict[str, int] = {}
        self._connection_reconnect_counts: dict[str, int] = {}
        self._connection_lifetime_total_ms: dict[str, int] = {}
        self._connection_lifetime_max_ms: dict[str, int] = {}
        self._connection_closed_counts: dict[str, int] = {}
        self._connected_source_keys: set[str] = set()
        self._utterance_counts: dict[str, int] = {}
        self._session_created_missing: dict[str, int] = {}
        self._session_update_failures: dict[str, int] = {}
        self._completed_missing: dict[str, int] = {}
        self._blank_partial_suppressed: dict[str, int] = {}
        self._vad_to_manual_fallbacks: dict[str, int] = {}
        self._idle_session_closures: dict[str, int] = {}
        self._append_counts: dict[str, int] = {}
        self._commit_counts: dict[str, int] = {}
        self._mode_by_source: dict[str, str] = {}
        self._connection_state_by_source: dict[str, str] = {}
        self._last_error_by_source: dict[str, str] = {}
        self._frames_before_first_partial: dict[str, int] = {}
        self._partial_listener: Callable[[AudioFrame, TranscriptResult], None] | None = None

    def set_partial_listener(self, listener: Callable[[AudioFrame, TranscriptResult], None]) -> None:
        """Publish provider partials from the receive pump, independent of audio appends."""
        self._partial_listener = listener

    def warm_session(
        self,
        *,
        session_id: str,
        source_kind: str,
        sample_rate_hz: int = 16_000,
        interview_language: InterviewLanguage = "zh-CN",
    ) -> None:
        """Create the role provider session without sending synthetic audio."""
        now_ms = int(time.time() * 1000)
        self._get_or_create_source_session(AudioFrame(
            publisher_id=f"prewarm:{session_id}:{source_kind}",
            session_id=session_id,
            device_id="prewarm",
            source_id=f"prewarm:{source_kind}",
            source_kind=source_kind,  # type: ignore[arg-type]
            segment_id=f"prewarm:{source_kind}",
            revision=0,
            sequence=0,
            captured_at_ms=now_ms,
            started_at_ms=now_ms,
            ended_at_ms=now_ms,
            duration_ms=0,
            codec="pcm-s16le",
            sample_rate_hz=sample_rate_hz,
            channels=1,
            is_final=False,
            audio_bytes=b"",
            interview_language=interview_language,
        ))

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
        try:
            (
                text,
                first_text_at_ms,
                partial_received_at_ms,
                completed_at_ms,
                audio_appended_at_ms,
                first_audio_appended_at_ms,
                commit_sent_at_ms,
                asr_lock_wait_start_at_ms,
                asr_lock_acquired_at_ms,
                qwen_send_enqueue_at_ms,
                qwen_ws_send_start_at_ms,
                qwen_ws_send_complete_at_ms,
                connection_id,
            ) = self._roundtrip(normalized_frame)
        finally:
            if not self.settings.realtime_asr_persistent_sessions_enabled:
                self._close_source_session(self._source_session_key(normalized_frame))
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
            partial_received_at_ms=partial_received_at_ms,
            completed_at_ms=completed_at_ms,
            audio_appended_at_ms=audio_appended_at_ms,
            first_audio_appended_at_ms=first_audio_appended_at_ms,
            commit_sent_at_ms=commit_sent_at_ms,
            asr_lock_wait_start_at_ms=asr_lock_wait_start_at_ms,
            asr_lock_acquired_at_ms=asr_lock_acquired_at_ms,
            qwen_send_enqueue_at_ms=qwen_send_enqueue_at_ms,
            qwen_ws_send_start_at_ms=qwen_ws_send_start_at_ms,
            qwen_ws_send_complete_at_ms=qwen_ws_send_complete_at_ms,
            connection_id=connection_id,
        )

    def finalize(self, *, frame: AudioFrame, attempt: int) -> TranscriptResult:
        """Provider boundary for an authoritative application-side turn commit."""
        return self.transcribe(frame=frame, attempt=attempt)

    def diagnostics(self, source_kind: str) -> dict[str, int | float]:
        now = time.monotonic()
        with self._source_sessions_lock:
            active_sessions = [
                session for session in self._source_sessions.values() if session.source_kind == source_kind
            ]
            active_provider_sessions = len(active_sessions)
            active_lifetime_ms = max(
                (int((now - session.created_at_monotonic) * 1000) for session in active_sessions),
                default=0,
            )
        create_count = self._connection_create_counts.get(source_kind, 0)
        utterance_count = self._utterance_counts.get(source_kind, 0)
        closed_count = self._connection_closed_counts.get(source_kind, 0)
        lifetime_total_ms = self._connection_lifetime_total_ms.get(source_kind, 0)
        return {
            "connection_recreations": self._connection_recreations.get(source_kind, 0),
            "asr_connection_create_count": create_count,
            "asr_connection_reconnect_count": self._connection_reconnect_counts.get(source_kind, 0),
            "asr_connection_lifetime_ms": active_lifetime_ms,
            "asr_connection_completed_lifetime_avg_ms": (
                int(lifetime_total_ms / closed_count) if closed_count else 0
            ),
            "asr_connection_completed_lifetime_max_ms": self._connection_lifetime_max_ms.get(source_kind, 0),
            "utterance_count": utterance_count,
            "utterances_per_connection": round(utterance_count / create_count, 3) if create_count else 0.0,
            "session_created_missing": self._session_created_missing.get(source_kind, 0),
            "session_update_failures": self._session_update_failures.get(source_kind, 0),
            "completed_missing": self._completed_missing.get(source_kind, 0),
            "blank_partial_suppressed": self._blank_partial_suppressed.get(source_kind, 0),
            "vad_to_manual_fallbacks": self._vad_to_manual_fallbacks.get(source_kind, 0),
            "idle_session_closures": self._idle_session_closures.get(source_kind, 0),
            "append_count": self._append_counts.get(source_kind, 0),
            "commit_count": self._commit_counts.get(source_kind, 0),
            "active_provider_sessions": active_provider_sessions,
            "frames_before_first_partial": self._frames_before_first_partial.get(source_kind, 0),
        }

    def runtime_status(self, source_kind: str) -> dict[str, str | int | None]:
        return {
            "mode": self._mode_by_source.get(source_kind),
            "connection_state": self._connection_state_by_source.get(source_kind),
            "last_error_code": self._last_error_by_source.get(source_kind),
            **self.diagnostics(source_kind),
        }

    def close_session(self, *, session_id: str) -> int:
        prefix = f"{session_id}:"
        with self._source_sessions_lock:
            source_session_keys = [
                source_session_key
                for source_session_key in self._source_sessions
                if source_session_key.startswith(prefix)
            ]
        for source_session_key in source_session_keys:
            self._close_source_session(source_session_key)
        return len(source_session_keys)

    def close_source(self, *, session_id: str, source_kind: str) -> int:
        source_session_key = f"{session_id}:{source_kind}"
        with self._source_sessions_lock:
            exists = source_session_key in self._source_sessions
        self._close_source_session(source_session_key)
        return 1 if exists else 0

    def _roundtrip(self, frame: AudioFrame) -> tuple[
        str,
        int | None,
        int | None,
        int | None,
        int | None,
        int | None,
        int | None,
        int | None,
        int | None,
        int | None,
        int | None,
        int | None,
        str,
    ]:
        session = self._get_or_create_source_session(frame)
        audio_appended_at_ms: int | None = None
        commit_sent_at_ms: int | None = None
        asr_lock_wait_start_at_ms = int(time.time() * 1000)
        try:
            with session.lock:
                asr_lock_acquired_at_ms = int(time.time() * 1000)
                self._prepare_segment_state(session, frame)
                with session.event_condition:
                    session.latest_frame = frame
                    session.latest_asr_lock_wait_start_at_ms = asr_lock_wait_start_at_ms
                    session.latest_asr_lock_acquired_at_ms = asr_lock_acquired_at_ms
                if frame.audio_bytes:
                    self._append_counts[frame.source_kind] = self._append_counts.get(frame.source_kind, 0) + ((len(frame.audio_bytes) + 6399) // 6400)
                    qwen_send_enqueue_at_ms = int(time.time() * 1000)
                    with session.event_condition:
                        session.latest_qwen_send_enqueue_at_ms = qwen_send_enqueue_at_ms
                        session.latest_qwen_ws_send_start_at_ms = qwen_send_enqueue_at_ms
                    qwen_ws_send_start_at_ms, qwen_ws_send_complete_at_ms = self._send_audio_chunks(
                        session.connection,
                        frame.audio_bytes,
                        event_id_prefix=f"{frame.segment_id}-{frame.revision}",
                    )
                    audio_appended_at_ms = int(time.time() * 1000)
                    with session.event_condition:
                        session.latest_audio_appended_at_ms = audio_appended_at_ms
                        if session.first_audio_appended_at_ms is None:
                            session.first_audio_appended_at_ms = audio_appended_at_ms
                        session.latest_qwen_ws_send_start_at_ms = qwen_ws_send_start_at_ms
                        session.latest_qwen_ws_send_complete_at_ms = qwen_ws_send_complete_at_ms
                    session.updated_at_monotonic = time.monotonic()
                if frame.is_final:
                    session.connection.send(json.dumps({
                        "event_id": f"rt-commit-{frame.segment_id}-{frame.revision}",
                        "type": "input_audio_buffer.commit",
                    }))
                    commit_sent_at_ms = int(time.time() * 1000)
                    self._commit_counts[frame.source_kind] = self._commit_counts.get(frame.source_kind, 0) + 1
                if frame.is_final or not self.settings.realtime_asr_nonblocking_partials_enabled:
                    transcript_text, first_text_at_ms, partial_received_at_ms, completed_at_ms = self._wait_for_transcript(
                        session,
                        finalize=frame.is_final,
                    )
                else:
                    transcript_text, first_text_at_ms, partial_received_at_ms, completed_at_ms = self._latest_available_transcript(
                        session
                    )
                if frame.is_final:
                    with session.event_condition:
                        # Freeze a completed utterance before releasing the source
                        # lock. Providers may still deliver an older partial after
                        # `completed`; it must not overwrite the final transcript or
                        # leak into the next segment.
                        session.accepting_transcript_events = False
                        session.current_segment_id = None
                self._connection_state_by_source[session.source_kind] = "receiving"
                self._last_error_by_source.pop(session.source_kind, None)
                return (
                    transcript_text,
                    first_text_at_ms,
                    partial_received_at_ms,
                    completed_at_ms,
                    audio_appended_at_ms,
                    session.first_audio_appended_at_ms,
                    commit_sent_at_ms,
                    asr_lock_wait_start_at_ms,
                    asr_lock_acquired_at_ms,
                    session.latest_qwen_send_enqueue_at_ms,
                    session.latest_qwen_ws_send_start_at_ms,
                    session.latest_qwen_ws_send_complete_at_ms,
                    session.connection_id,
                )
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
        except RetryableAsrError:
            # A missing final or receiver failure leaves provider-side utterance
            # state ambiguous. Recreate the source session before retrying instead
            # of allowing late events to contaminate the next segment.
            self._close_source_session(self._source_session_key(frame))
            raise

    def _source_session_key(self, frame: AudioFrame) -> str:
        return f"{frame.session_id}:{frame.source_kind}"

    def _prepare_segment_state(self, session: _SourceRealtimeSession, frame: AudioFrame) -> None:
        if session.current_segment_id == frame.segment_id:
            return
        with session.event_condition:
            session.current_segment_id = frame.segment_id
            session.source_generation = frame.source_generation or session.source_generation
            self._utterance_counts[frame.source_kind] = self._utterance_counts.get(frame.source_kind, 0) + 1
            session.transcript_text = ""
            session.first_text_at_ms = None
            session.latest_text_at_ms = None
            session.completed_at_ms = None
            session.receiver_error = None
            session.accepting_transcript_events = True
            session.first_partial_observed_for_segment = False
            session.latest_audio_appended_at_ms = None
            session.first_audio_appended_at_ms = None
            session.latest_asr_lock_wait_start_at_ms = None
            session.latest_asr_lock_acquired_at_ms = None
            session.latest_qwen_send_enqueue_at_ms = None
            session.latest_qwen_ws_send_start_at_ms = None
            session.latest_qwen_ws_send_complete_at_ms = None
            session.delivered_revision = session.event_revision

    def _get_or_create_source_session(self, frame: AudioFrame) -> _SourceRealtimeSession:
        key = self._source_session_key(frame)
        with self._source_sessions_lock:
            self._sweep_stale_sessions_locked()
            existing = self._source_sessions.get(key)
            if existing is not None:
                reusable = (
                    self.settings.realtime_asr_persistent_sessions_enabled
                    and existing.sample_rate_hz == frame.sample_rate_hz
                    and existing.interview_language == frame.interview_language
                )
                if reusable:
                    existing.source_generation = frame.source_generation or existing.source_generation
                    existing.updated_at_monotonic = time.monotonic()
                    return existing
                self._source_sessions.pop(key, None)
                self._record_closed_lifetime(existing)
                try:
                    existing.connection.close()
                except Exception:
                    pass
            connection, mode = self._open_connection(frame)
            self._connection_recreations[frame.source_kind] = self._connection_recreations.get(frame.source_kind, 0) + 1
            self._connection_create_counts[frame.source_kind] = self._connection_create_counts.get(frame.source_kind, 0) + 1
            if key in self._connected_source_keys:
                self._connection_reconnect_counts[frame.source_kind] = self._connection_reconnect_counts.get(frame.source_kind, 0) + 1
            else:
                self._connected_source_keys.add(key)
            session = _SourceRealtimeSession(
                connection=connection,
                sample_rate_hz=frame.sample_rate_hz,
                created_at_monotonic=time.monotonic(),
                updated_at_monotonic=time.monotonic(),
                source_session_key=key,
                source_kind=frame.source_kind,
                interview_language=frame.interview_language,
                connection_id=f"{frame.source_kind}-{self._connection_create_counts[frame.source_kind]}",
                source_generation=frame.source_generation or 1,
                mode=mode,
            )
            self._source_sessions[key] = session
            receiver = threading.Thread(
                target=self._receive_events,
                args=(session,),
                name=f"realtime-asr-recv-{frame.source_kind}",
                daemon=True,
            )
            session.receiver_thread = receiver
            receiver.start()
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
        self.logger.info(
            "realtime_asr.language_route",
            extra={
                "interview_language": frame.interview_language,
                "source_kind": frame.source_kind,
                "stage": "session-update",
                "prompt_template_id": None,
                "prompt_version": None,
            },
        )
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
                "language": "en" if frame.interview_language == "en-US" else "zh",
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

    def _wait_for_transcript(
        self,
        session: _SourceRealtimeSession,
        *,
        finalize: bool,
    ) -> tuple[str, int | None, int | None, int | None]:
        wait_seconds = (
            self.settings.realtime_asr_finalize_timeout_seconds
            if finalize
            else self.settings.realtime_asr_partial_timeout_seconds
        )
        deadline = time.monotonic() + max(0.006, wait_seconds)
        with session.event_condition:
            while True:
                if session.receiver_error is not None:
                    raise RetryableAsrError("realtime_asr_connection_failed") from session.receiver_error
                if finalize and session.completed_at_ms is not None:
                    break
                if not finalize and session.event_revision > session.delivered_revision:
                    break
                remaining = deadline - time.monotonic()
                if remaining <= 0:
                    break
                session.event_condition.wait(timeout=remaining)
            has_new_revision = session.event_revision > session.delivered_revision
            transcript_text = session.transcript_text if finalize or has_new_revision else ""
            first_text_at_ms = session.first_text_at_ms
            partial_received_at_ms = session.latest_text_at_ms if has_new_revision else None
            completed_at_ms = session.completed_at_ms
            if has_new_revision:
                session.delivered_revision = session.event_revision
        if finalize and completed_at_ms is None:
            self._completed_missing[session.source_kind] = self._completed_missing.get(session.source_kind, 0) + 1
            raise RetryableAsrError("realtime_asr_transcript_missing")
        return transcript_text, first_text_at_ms, partial_received_at_ms, completed_at_ms

    @staticmethod
    def _latest_available_transcript(
        session: _SourceRealtimeSession,
    ) -> tuple[str, int | None, int | None, int | None]:
        """Return an already-received partial without delaying audio publication.

        The provider receiver owns transcript arrival. Audio append calls must not
        wait for that independent network event; a later append or the final
        commit will deliver the newest authoritative revision.
        """
        with session.event_condition:
            if session.receiver_error is not None:
                raise RetryableAsrError("realtime_asr_connection_failed") from session.receiver_error
            has_new_revision = session.event_revision > session.delivered_revision
            transcript_text = session.transcript_text if has_new_revision else ""
            if has_new_revision:
                session.delivered_revision = session.event_revision
            return (
                transcript_text,
                session.first_text_at_ms,
                session.latest_text_at_ms if has_new_revision else None,
                session.completed_at_ms,
            )

    def _receive_events(self, session: _SourceRealtimeSession) -> None:
        while True:
            with session.event_condition:
                if session.closed:
                    return
            try:
                raw = session.connection.recv(timeout=1.0)
            except TimeoutError:
                continue
            except Exception as exc:
                with session.event_condition:
                    if not session.closed:
                        session.receiver_error = exc
                        session.event_condition.notify_all()
                return
            try:
                message = json.loads(raw)
            except json.JSONDecodeError as exc:
                with session.event_condition:
                    session.receiver_error = exc
                    session.event_condition.notify_all()
                return
            event_type = message.get("type")
            if event_type == "error":
                with session.event_condition:
                    session.receiver_error = NonRetryableAsrError(self._error_message(message))
                    session.event_condition.notify_all()
                return
            if event_type == "session.updated":
                continue
            if event_type in {"conversation.item.input_audio_transcription.text", "conversation.item.input_audio_transcription.completed"}:
                partial_notification: tuple[AudioFrame, TranscriptResult] | None = None
                with session.event_condition:
                    if not session.accepting_transcript_events:
                        continue
                    if (
                        event_type == "conversation.item.input_audio_transcription.text"
                        and session.completed_at_ms is not None
                    ):
                        # The completed transcript is authoritative. A delayed
                        # partial from the same provider buffer cannot revise it.
                        continue
                    next_text = (
                        message.get("transcript")
                        or message.get("text")
                        or message.get("stash")
                        or session.transcript_text
                    )
                    if isinstance(next_text, str) and next_text.strip():
                        session.transcript_text = next_text
                        if session.first_text_at_ms is None:
                            session.first_text_at_ms = int(time.time() * 1000)
                        session.latest_text_at_ms = int(time.time() * 1000)
                        session.event_revision += 1
                        if (
                            event_type == "conversation.item.input_audio_transcription.text"
                            and self._partial_listener is not None
                            and session.latest_frame is not None
                        ):
                            if not session.first_partial_observed_for_segment:
                                session.first_partial_observed_for_segment = True
                                self._frames_before_first_partial[session.source_kind] = session.latest_frame.revision
                            # Mark this provider revision delivered before invoking
                            # the listener so the next audio append cannot publish
                            # the same partial a second time.
                            session.delivered_revision = session.event_revision
                            partial_frame = replace(session.latest_frame, is_final=False)
                            partial_notification = (
                                partial_frame,
                                TranscriptResult(
                                    text=next_text.strip(),
                                    confidence=0.82,
                                    overlap=False,
                                    usage=AsrUsageReport(
                                        total_tokens=max(1, len(next_text.strip()) // 2),
                                        provider_name=self.settings.realtime_asr_provider,
                                        model_name=self.settings.realtime_asr_model,
                                    ),
                                    first_text_at_ms=session.first_text_at_ms,
                                    partial_received_at_ms=session.latest_text_at_ms,
                                    audio_appended_at_ms=session.latest_audio_appended_at_ms,
                                    first_audio_appended_at_ms=session.first_audio_appended_at_ms,
                                    asr_lock_wait_start_at_ms=session.latest_asr_lock_wait_start_at_ms,
                                    asr_lock_acquired_at_ms=session.latest_asr_lock_acquired_at_ms,
                                    qwen_send_enqueue_at_ms=session.latest_qwen_send_enqueue_at_ms,
                                    qwen_ws_send_start_at_ms=session.latest_qwen_ws_send_start_at_ms,
                                    qwen_ws_send_complete_at_ms=session.latest_qwen_ws_send_complete_at_ms,
                                    provider_revision=session.event_revision,
                                    connection_id=session.connection_id,
                                ),
                            )
                    elif event_type == "conversation.item.input_audio_transcription.text":
                        source_kind = session.source_kind
                        self._blank_partial_suppressed[source_kind] = self._blank_partial_suppressed.get(source_kind, 0) + 1
                    if event_type == "conversation.item.input_audio_transcription.completed":
                        session.completed_at_ms = int(time.time() * 1000)
                        session.event_revision += 1
                    session.event_condition.notify_all()
                if partial_notification is not None and self._partial_listener is not None:
                    try:
                        self._partial_listener(*partial_notification)
                    except Exception as exc:  # The receive pump must remain alive.
                        self.logger.exception(
                            "realtime_asr.partial_listener_failed",
                            extra={"sourceKind": session.source_kind, "errorCode": exc.__class__.__name__},
                        )

    def _close_source_session(self, source_session_key: str) -> None:
        with self._source_sessions_lock:
            session = self._source_sessions.pop(source_session_key, None)
        if session is None:
            return
        self._record_closed_lifetime(session)
        self._connection_state_by_source[session.source_kind] = "closed"
        with session.event_condition:
            session.closed = True
            session.event_condition.notify_all()
        try:
            session.connection.close()
        except Exception:
            pass

    def _record_closed_lifetime(self, session: _SourceRealtimeSession) -> None:
        lifetime_ms = max(0, int((time.monotonic() - session.created_at_monotonic) * 1000))
        closed_counts = getattr(self, "_connection_closed_counts", None)
        if closed_counts is None:
            closed_counts = self._connection_closed_counts = {}
        lifetime_totals = getattr(self, "_connection_lifetime_total_ms", None)
        if lifetime_totals is None:
            lifetime_totals = self._connection_lifetime_total_ms = {}
        lifetime_maximums = getattr(self, "_connection_lifetime_max_ms", None)
        if lifetime_maximums is None:
            lifetime_maximums = self._connection_lifetime_max_ms = {}
        closed_counts[session.source_kind] = closed_counts.get(session.source_kind, 0) + 1
        lifetime_totals[session.source_kind] = lifetime_totals.get(session.source_kind, 0) + lifetime_ms
        lifetime_maximums[session.source_kind] = max(
            lifetime_maximums.get(session.source_kind, 0),
            lifetime_ms,
        )

    def _sweep_stale_sessions_locked(self) -> None:
        # A commercial persistent session follows the interview lifecycle. Do
        # not deliberately introduce a cold reconnect after a quiet interval;
        # explicit pause/end and provider/network failures own closure.
        if getattr(self.settings, "realtime_asr_persistent_sessions_enabled", False):
            return
        now = time.monotonic()
        stale_session_keys = [
            source_session_key
            for source_session_key, session in self._source_sessions.items()
            if now - session.updated_at_monotonic > max(30, self.settings.realtime_asr_session_idle_seconds)
        ]
        for source_session_key in stale_session_keys:
            session = self._source_sessions.pop(source_session_key, None)
            if session is None:
                continue
            self._record_closed_lifetime(session)
            self._idle_session_closures[session.source_kind] = self._idle_session_closures.get(session.source_kind, 0) + 1
            self._connection_state_by_source[session.source_kind] = "idle"
            with session.event_condition:
                session.closed = True
                session.event_condition.notify_all()
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
    def _send_audio_chunks(websocket, audio_bytes: bytes, *, event_id_prefix: str = "audio") -> tuple[int, int]:
        started_at_ms = int(time.time() * 1000)
        if not audio_bytes:
            return started_at_ms, started_at_ms
        # 6,400 bytes is 200 ms of 16 kHz mono PCM16. It keeps partial
        # transcripts responsive without multiplying synchronous WS writes.
        for index in range(0, len(audio_bytes), 6400):
            chunk = audio_bytes[index : index + 6400]
            websocket.send(json.dumps({
                "event_id": f"rt-audio-{event_id_prefix}-{index // 6400}",
                "type": "input_audio_buffer.append",
                "audio": base64.b64encode(chunk).decode("ascii"),
            }))
        return started_at_ms, int(time.time() * 1000)

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
