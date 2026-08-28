from __future__ import annotations

import json
import logging
import threading
import time
from dataclasses import dataclass, field, replace
from typing import Callable
from uuid import uuid4

from websockets.exceptions import ConnectionClosed
from websockets.sync.client import connect

from app.core.config import Settings
from app.core.logging import log_event
from app.ports.interview_session import InterviewLanguage
from app.ports.realtime_speech import AsrUsageReport, AudioFrame, RealtimeAsrGatewayPort, TranscriptResult
from app.services.realtime_speech_service import NonRetryableAsrError, RetryableAsrError


@dataclass
class _SourceTaskSession:
    connection: object
    sample_rate_hz: int
    interview_language: InterviewLanguage
    source_session_key: str
    source_kind: str
    connection_id: str
    created_at_monotonic: float
    updated_at_monotonic: float
    source_generation: int = 1
    task_id: str | None = None
    task_started: bool = False
    task_finished: bool = False
    current_segment_id: str | None = None
    sentence_texts: dict[int, str] = field(default_factory=dict)
    transcript_text: str = ""
    event_revision: int = 0
    delivered_revision: int = 0
    first_text_at_ms: int | None = None
    latest_text_at_ms: int | None = None
    completed_at_ms: int | None = None
    sentence_final_revision: int = 0
    segment_sentence_final_revision: int = 0
    latest_sentence_final_at_ms: int | None = None
    receiver_error: Exception | None = None
    provider_failure_code: str | None = None
    provider_failure_message: str | None = None
    accepting_transcript_events: bool = True
    closed: bool = False
    latest_frame: AudioFrame | None = None
    latest_audio_appended_at_ms: int | None = None
    first_audio_appended_at_ms: int | None = None
    latest_asr_lock_wait_start_at_ms: int | None = None
    latest_asr_lock_acquired_at_ms: int | None = None
    latest_qwen_send_enqueue_at_ms: int | None = None
    latest_qwen_ws_send_start_at_ms: int | None = None
    latest_qwen_ws_send_complete_at_ms: int | None = None
    lock: threading.Lock = field(default_factory=threading.Lock)
    event_condition: threading.Condition = field(default_factory=threading.Condition)
    receiver_thread: threading.Thread | None = None


class DashScopeTaskAsrGateway(RealtimeAsrGatewayPort):
    """DashScope inference-task adapter for Qwen Audio 3 streaming ASR."""

    def __init__(self, settings: Settings, logger: logging.Logger) -> None:
        self.settings = settings
        self.logger = logger
        self._source_sessions: dict[str, _SourceTaskSession] = {}
        self._source_sessions_lock = threading.Lock()
        self._source_creation_locks: dict[str, threading.Lock] = {}
        self._connected_source_keys: set[str] = set()
        self._partial_listener: Callable[[AudioFrame, TranscriptResult], None] | None = None
        self._connection_create_counts: dict[str, int] = {}
        self._connection_reconnect_counts: dict[str, int] = {}
        self._connection_closed_counts: dict[str, int] = {}
        self._connection_lifetime_total_ms: dict[str, int] = {}
        self._connection_lifetime_max_ms: dict[str, int] = {}
        self._task_start_counts: dict[str, int] = {}
        self._task_finish_counts: dict[str, int] = {}
        self._task_failure_counts: dict[str, int] = {}
        self._partial_counts: dict[str, int] = {}
        self._final_counts: dict[str, int] = {}
        self._provider_sentence_final_counts: dict[str, int] = {}
        self._blank_result_counts: dict[str, int] = {}
        self._timeout_counts: dict[str, int] = {}
        self._append_counts: dict[str, int] = {}
        self._utterance_counts: dict[str, int] = {}
        self._connection_state_by_source: dict[str, str] = {}
        self._last_error_by_source: dict[str, str] = {}

    def set_partial_listener(self, listener: Callable[[AudioFrame, TranscriptResult], None]) -> None:
        self._partial_listener = listener

    def warm_session(
        self,
        *,
        session_id: str,
        source_kind: str,
        sample_rate_hz: int = 16_000,
        interview_language: InterviewLanguage = "zh-CN",
    ) -> None:
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

    def transcribe(self, *, frame: AudioFrame, attempt: int) -> TranscriptResult:
        del attempt
        if not self.settings.realtime_asr_api_key:
            raise NonRetryableAsrError("realtime_asr_api_key_missing")
        if self._normalize_audio_codec(frame.codec) != "pcm-s16le":
            raise NonRetryableAsrError("unsupported_audio_codec")
        if frame.sample_rate_hz <= 0 or frame.channels != 1:
            raise NonRetryableAsrError("invalid_audio_metadata")
        return self._roundtrip(replace(frame, codec="pcm-s16le"))

    def finalize(self, *, frame: AudioFrame, attempt: int) -> TranscriptResult:
        return self.transcribe(frame=frame, attempt=attempt)

    def diagnostics(self, source_kind: str) -> dict[str, int | float]:
        now = time.monotonic()
        with self._source_sessions_lock:
            active = [item for item in self._source_sessions.values() if item.source_kind == source_kind]
        creates = self._connection_create_counts.get(source_kind, 0)
        utterances = self._utterance_counts.get(source_kind, 0)
        closed = self._connection_closed_counts.get(source_kind, 0)
        return {
            "connection_recreations": creates,
            "asr_connection_create_count": creates,
            "asr_connection_reconnect_count": self._connection_reconnect_counts.get(source_kind, 0),
            "asr_connection_lifetime_ms": max(
                (int((now - item.created_at_monotonic) * 1000) for item in active), default=0
            ),
            "asr_connection_completed_lifetime_avg_ms": (
                int(self._connection_lifetime_total_ms.get(source_kind, 0) / closed) if closed else 0
            ),
            "asr_connection_completed_lifetime_max_ms": self._connection_lifetime_max_ms.get(source_kind, 0),
            "active_provider_sessions": len(active),
            "task_start_count": self._task_start_counts.get(source_kind, 0),
            "task_finish_count": self._task_finish_counts.get(source_kind, 0),
            "task_failure_count": self._task_failure_counts.get(source_kind, 0),
            "partial_count": self._partial_counts.get(source_kind, 0),
            "final_count": self._final_counts.get(source_kind, 0),
            "provider_sentence_final_count": self._provider_sentence_final_counts.get(source_kind, 0),
            "blank_result_suppressed": self._blank_result_counts.get(source_kind, 0),
            "provider_timeout_count": self._timeout_counts.get(source_kind, 0),
            "append_count": self._append_counts.get(source_kind, 0),
            "utterance_count": utterances,
            "utterances_per_connection": round(utterances / creates, 3) if creates else 0.0,
        }

    def runtime_status(self, source_kind: str) -> dict[str, str | int | float | None]:
        return {
            "protocol": "qwen-audio-task",
            "model": self.settings.realtime_asr_model,
            "mode": "provider-vad-task",
            "continuous_task_enabled": int(self.settings.realtime_asr_continuous_task_enabled),
            "connection_state": self._connection_state_by_source.get(source_kind),
            "last_error_code": self._last_error_by_source.get(source_kind),
            **self.diagnostics(source_kind),
        }

    def close_source(self, *, session_id: str, source_kind: str) -> int:
        key = f"{session_id}:{source_kind}"
        with self._source_sessions_lock:
            exists = key in self._source_sessions
        self._close_source_session(key)
        return 1 if exists else 0

    def close_session(self, *, session_id: str) -> int:
        prefix = f"{session_id}:"
        with self._source_sessions_lock:
            keys = [key for key in self._source_sessions if key.startswith(prefix)]
        for key in keys:
            self._close_source_session(key)
        return len(keys)

    def _roundtrip(self, frame: AudioFrame) -> TranscriptResult:
        session = self._get_or_create_source_session(frame)
        lock_wait_at_ms = int(time.time() * 1000)
        try:
            with session.lock:
                lock_acquired_at_ms = int(time.time() * 1000)
                self._ensure_task_started(session)
                self._prepare_segment_state(session, frame)
                with session.event_condition:
                    session.latest_frame = frame
                    session.latest_asr_lock_wait_start_at_ms = lock_wait_at_ms
                    session.latest_asr_lock_acquired_at_ms = lock_acquired_at_ms
                audio_appended_at_ms = None
                if frame.audio_bytes:
                    enqueue_at_ms = int(time.time() * 1000)
                    with session.event_condition:
                        session.latest_qwen_send_enqueue_at_ms = enqueue_at_ms
                    send_start_at_ms, send_complete_at_ms = self._send_audio_chunks(
                        session.connection, frame.audio_bytes
                    )
                    audio_appended_at_ms = int(time.time() * 1000)
                    self._append_counts[frame.source_kind] = self._append_counts.get(frame.source_kind, 0) + (
                        (len(frame.audio_bytes) + 6399) // 6400
                    )
                    with session.event_condition:
                        session.latest_audio_appended_at_ms = audio_appended_at_ms
                        if session.first_audio_appended_at_ms is None:
                            session.first_audio_appended_at_ms = audio_appended_at_ms
                        session.latest_qwen_ws_send_start_at_ms = send_start_at_ms
                        session.latest_qwen_ws_send_complete_at_ms = send_complete_at_ms
                    session.updated_at_monotonic = time.monotonic()

                if frame.is_final:
                    commit_sent_at_ms = int(time.time() * 1000)
                    continuous_completed = False
                    if self.settings.realtime_asr_continuous_task_enabled:
                        continuous_completed = self._wait_for_sentence_final(session)
                    if continuous_completed:
                        text, first_text_at_ms, partial_at_ms, completed_at_ms = self._current_segment_result(session)
                    else:
                        self._finish_task(session)
                        text, first_text_at_ms, partial_at_ms, completed_at_ms = self._wait_for_final(session)
                    result = self._result(
                        session,
                        text=text,
                        confidence=0.96,
                        first_text_at_ms=first_text_at_ms,
                        partial_received_at_ms=partial_at_ms,
                        completed_at_ms=completed_at_ms,
                        audio_appended_at_ms=audio_appended_at_ms,
                        commit_sent_at_ms=commit_sent_at_ms,
                        lock_wait_at_ms=lock_wait_at_ms,
                        lock_acquired_at_ms=lock_acquired_at_ms,
                    )
                    self._final_counts[frame.source_kind] = self._final_counts.get(frame.source_kind, 0) + 1
                    with session.event_condition:
                        session.current_segment_id = None
                        session.accepting_transcript_events = True
                    if not continuous_completed:
                        self._start_task(session, wait=False)
                    self._connection_state_by_source[frame.source_kind] = "ready"
                    self._last_error_by_source.pop(frame.source_kind, None)
                    return result

                text, first_text_at_ms, partial_at_ms, completed_at_ms = self._latest_available_transcript(session)
                self._connection_state_by_source[frame.source_kind] = "receiving"
                self._last_error_by_source.pop(frame.source_kind, None)
                return self._result(
                    session,
                    text=text,
                    confidence=0.82,
                    first_text_at_ms=first_text_at_ms,
                    partial_received_at_ms=partial_at_ms,
                    completed_at_ms=completed_at_ms,
                    audio_appended_at_ms=audio_appended_at_ms,
                    commit_sent_at_ms=None,
                    lock_wait_at_ms=lock_wait_at_ms,
                    lock_acquired_at_ms=lock_acquired_at_ms,
                )
        except NonRetryableAsrError:
            self._close_source_session(self._source_session_key(frame))
            raise
        except RetryableAsrError:
            self._close_source_session(self._source_session_key(frame))
            raise
        except TimeoutError as exc:
            self._timeout_counts[frame.source_kind] = self._timeout_counts.get(frame.source_kind, 0) + 1
            self._record_error(frame.source_kind, "realtime_asr_timeout")
            self._close_source_session(self._source_session_key(frame))
            raise RetryableAsrError("realtime_asr_timeout") from exc
        except (OSError, ConnectionClosed, json.JSONDecodeError) as exc:
            self._record_error(frame.source_kind, "realtime_asr_connection_failed")
            self._close_source_session(self._source_session_key(frame))
            raise RetryableAsrError("realtime_asr_connection_failed") from exc

    def _get_or_create_source_session(self, frame: AudioFrame) -> _SourceTaskSession:
        key = self._source_session_key(frame)
        with self._source_sessions_lock:
            creation_lock = self._source_creation_locks.setdefault(key, threading.Lock())
        with creation_lock:
            with self._source_sessions_lock:
                existing = self._source_sessions.get(key)
                if existing is not None and (
                    existing.sample_rate_hz == frame.sample_rate_hz
                    and existing.interview_language == frame.interview_language
                    and not existing.closed
                ):
                    existing.source_generation = frame.source_generation or existing.source_generation
                    existing.updated_at_monotonic = time.monotonic()
                    return existing
                if existing is not None:
                    self._source_sessions.pop(key, None)
            if existing is not None:
                self._close_detached_session(existing)

            connection = connect(
                self._connect_url(),
                additional_headers={"Authorization": f"Bearer {self.settings.realtime_asr_api_key}"},
                open_timeout=min(
                    self.settings.realtime_asr_connect_timeout_seconds,
                    self.settings.integration_http_timeout_seconds,
                ),
                close_timeout=min(
                    self.settings.realtime_asr_connect_timeout_seconds,
                    self.settings.integration_http_timeout_seconds,
                ),
                ping_interval=20,
                ping_timeout=20,
                max_size=2_097_152,
                logger=self.logger,
            )
            create_count = self._connection_create_counts.get(frame.source_kind, 0) + 1
            self._connection_create_counts[frame.source_kind] = create_count
            if key in self._connected_source_keys:
                self._connection_reconnect_counts[frame.source_kind] = (
                    self._connection_reconnect_counts.get(frame.source_kind, 0) + 1
                )
            else:
                self._connected_source_keys.add(key)
            session = _SourceTaskSession(
                connection=connection,
                sample_rate_hz=frame.sample_rate_hz,
                interview_language=frame.interview_language,
                source_session_key=key,
                source_kind=frame.source_kind,
                connection_id=f"{frame.source_kind}-task-{create_count}",
                created_at_monotonic=time.monotonic(),
                updated_at_monotonic=time.monotonic(),
                source_generation=frame.source_generation or 1,
            )
            with self._source_sessions_lock:
                self._source_sessions[key] = session
            receiver = threading.Thread(
                target=self._receive_events,
                args=(session,),
                name=f"qwen-audio-task-recv-{frame.source_kind}",
                daemon=True,
            )
            session.receiver_thread = receiver
            receiver.start()
            with session.lock:
                self._start_task(session, wait=True)
            self._connection_state_by_source[frame.source_kind] = "ready"
            return session

    def _start_task(self, session: _SourceTaskSession, *, wait: bool) -> None:
        task_id = str(uuid4())
        with session.event_condition:
            session.task_id = task_id
            session.task_started = False
            session.task_finished = False
            session.current_segment_id = None
            session.sentence_texts = {}
            session.transcript_text = ""
            session.first_text_at_ms = None
            session.latest_text_at_ms = None
            session.completed_at_ms = None
            session.sentence_final_revision = 0
            session.segment_sentence_final_revision = 0
            session.latest_sentence_final_at_ms = None
            session.receiver_error = None
            session.provider_failure_code = None
            session.provider_failure_message = None
            session.accepting_transcript_events = True
            session.delivered_revision = session.event_revision
        session.connection.send(json.dumps({
            "header": {"action": "run-task", "task_id": task_id, "streaming": "duplex"},
            "payload": {
                "task_group": "audio",
                "task": "asr",
                "function": "recognition",
                "model": self.settings.realtime_asr_model,
                "parameters": {
                    "format": "pcm",
                    "sample_rate": session.sample_rate_hz,
                    "language_hints": ["en" if session.interview_language == "en-US" else "zh"],
                    "semantic_punctuation_enabled": False,
                    "max_sentence_silence": max(
                        200, min(6000, int(self.settings.realtime_asr_max_sentence_silence_ms))
                    ),
                    "heartbeat": True,
                },
                "input": {},
            },
        }))
        self._task_start_counts[session.source_kind] = self._task_start_counts.get(session.source_kind, 0) + 1
        if wait:
            self._ensure_task_started(session)

    def _ensure_task_started(self, session: _SourceTaskSession) -> None:
        deadline = time.monotonic() + max(0.1, self.settings.realtime_asr_connect_timeout_seconds)
        with session.event_condition:
            while not session.task_started:
                self._raise_receiver_error(session)
                remaining = deadline - time.monotonic()
                if remaining <= 0:
                    raise TimeoutError("qwen_audio_task_start_timeout")
                session.event_condition.wait(timeout=remaining)

    def _prepare_segment_state(self, session: _SourceTaskSession, frame: AudioFrame) -> None:
        if session.current_segment_id == frame.segment_id:
            return
        with session.event_condition:
            if session.current_segment_id is not None:
                raise RetryableAsrError("realtime_asr_segment_overlap")
            session.current_segment_id = frame.segment_id
            session.source_generation = frame.source_generation or session.source_generation
            session.latest_frame = frame
            session.first_audio_appended_at_ms = None
            session.latest_audio_appended_at_ms = None
            session.latest_asr_lock_wait_start_at_ms = None
            session.latest_asr_lock_acquired_at_ms = None
            session.latest_qwen_send_enqueue_at_ms = None
            session.latest_qwen_ws_send_start_at_ms = None
            session.latest_qwen_ws_send_complete_at_ms = None
            session.sentence_texts = {}
            session.transcript_text = ""
            session.first_text_at_ms = None
            session.latest_text_at_ms = None
            session.completed_at_ms = None
            session.segment_sentence_final_revision = session.sentence_final_revision
            session.accepting_transcript_events = True
            self._utterance_counts[frame.source_kind] = self._utterance_counts.get(frame.source_kind, 0) + 1

    def _finish_task(self, session: _SourceTaskSession) -> None:
        if not session.task_id:
            raise RetryableAsrError("realtime_asr_task_missing")
        session.connection.send(json.dumps({
            "header": {"action": "finish-task", "task_id": session.task_id, "streaming": "duplex"},
            "payload": {"input": {}},
        }))

    def _wait_for_final(self, session: _SourceTaskSession) -> tuple[str, int | None, int | None, int | None]:
        deadline = time.monotonic() + max(0.1, self.settings.realtime_asr_finalize_timeout_seconds)
        with session.event_condition:
            while not session.task_finished:
                self._raise_receiver_error(session)
                remaining = deadline - time.monotonic()
                if remaining <= 0:
                    raise TimeoutError("qwen_audio_task_finish_timeout")
                session.event_condition.wait(timeout=remaining)
            session.delivered_revision = session.event_revision
            return (
                session.transcript_text,
                session.first_text_at_ms,
                session.latest_text_at_ms,
                session.completed_at_ms,
            )

    def _wait_for_sentence_final(self, session: _SourceTaskSession) -> bool:
        deadline = time.monotonic() + max(
            0.1,
            min(
                self.settings.realtime_asr_finalize_timeout_seconds,
                self.settings.realtime_asr_continuous_task_sentence_wait_seconds,
            ),
        )
        with session.event_condition:
            while (
                session.sentence_final_revision <= session.segment_sentence_final_revision
                or session.latest_sentence_final_at_ms is None
                or (
                    session.latest_audio_appended_at_ms is not None
                    and session.latest_sentence_final_at_ms < session.latest_audio_appended_at_ms
                )
            ):
                self._raise_receiver_error(session)
                remaining = deadline - time.monotonic()
                if remaining <= 0:
                    return False
                session.event_condition.wait(timeout=remaining)
            session.delivered_revision = session.event_revision
            return True

    @staticmethod
    def _current_segment_result(
        session: _SourceTaskSession,
    ) -> tuple[str, int | None, int | None, int | None]:
        with session.event_condition:
            return (
                session.transcript_text,
                session.first_text_at_ms,
                session.latest_text_at_ms,
                session.completed_at_ms,
            )

    @staticmethod
    def _latest_available_transcript(
        session: _SourceTaskSession,
    ) -> tuple[str, int | None, int | None, int | None]:
        with session.event_condition:
            if session.receiver_error is not None:
                raise session.receiver_error
            has_new_revision = session.event_revision > session.delivered_revision
            text = session.transcript_text if has_new_revision else ""
            if has_new_revision:
                session.delivered_revision = session.event_revision
            return (
                text,
                session.first_text_at_ms,
                session.latest_text_at_ms if has_new_revision else None,
                session.completed_at_ms,
            )

    def _receive_events(self, session: _SourceTaskSession) -> None:
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
                        if session.receiver_error is None:
                            session.receiver_error = exc
                        session.event_condition.notify_all()
                if not session.closed:
                    close_code, close_reason = self._connection_close_details(exc)
                    log_event(
                        self.logger,
                        logging.WARNING,
                        settings=self.settings,
                        event="realtime_asr.connection_closed",
                        feature="realtime-asr",
                        action="provider-receive",
                        source_kind=session.source_kind,
                        connection_id=session.connection_id,
                        task_id=session.task_id,
                        provider_code=session.provider_failure_code,
                        connection_lifetime_ms=max(
                            0, int((time.monotonic() - session.created_at_monotonic) * 1000)
                        ),
                        close_code=close_code,
                        close_reason=close_reason,
                    )
                return
            try:
                message = json.loads(raw)
            except (json.JSONDecodeError, TypeError) as exc:
                with session.event_condition:
                    if session.receiver_error is None:
                        session.receiver_error = exc
                    session.event_condition.notify_all()
                return
            header = message.get("header") or {}
            event = header.get("event")
            task_id = header.get("task_id")
            partial_notification: tuple[AudioFrame, TranscriptResult] | None = None
            with session.event_condition:
                if task_id and task_id != session.task_id:
                    continue
                if event == "task-started":
                    session.task_started = True
                    session.event_condition.notify_all()
                    continue
                if event == "task-failed":
                    code = str(header.get("error_code") or "realtime_asr_task_failed")
                    detail = str(header.get("error_message") or code)
                    self._task_failure_counts[session.source_kind] = self._task_failure_counts.get(session.source_kind, 0) + 1
                    self._record_error(session.source_kind, code)
                    if session.receiver_error is None:
                        session.receiver_error = self._provider_error(code, detail)
                        session.provider_failure_code = code[:128]
                        session.provider_failure_message = detail[:256]
                    session.event_condition.notify_all()
                    log_event(
                        self.logger,
                        logging.WARNING,
                        settings=self.settings,
                        event="realtime_asr.task_failed",
                        feature="realtime-asr",
                        action="provider-task",
                        source_kind=session.source_kind,
                        connection_id=session.connection_id,
                        task_id=session.task_id,
                        provider_code=code[:128],
                        provider_message=detail[:256],
                        connection_lifetime_ms=max(
                            0, int((time.monotonic() - session.created_at_monotonic) * 1000)
                        ),
                    )
                    continue
                if event == "task-finished":
                    session.task_finished = True
                    session.completed_at_ms = int(time.time() * 1000)
                    self._task_finish_counts[session.source_kind] = self._task_finish_counts.get(session.source_kind, 0) + 1
                    session.event_condition.notify_all()
                    continue
                if event != "result-generated" or not session.accepting_transcript_events:
                    continue
                sentence = (((message.get("payload") or {}).get("output") or {}).get("sentence") or {})
                text = sentence.get("text")
                if sentence.get("heartbeat") or not isinstance(text, str) or not text.strip():
                    self._blank_result_counts[session.source_kind] = self._blank_result_counts.get(session.source_kind, 0) + 1
                    continue
                sentence_id = int(sentence.get("sentence_id") or 0)
                session.sentence_texts[sentence_id] = text.strip()
                combined = "".join(session.sentence_texts[index] for index in sorted(session.sentence_texts))
                now_ms = int(time.time() * 1000)
                session.transcript_text = combined
                if session.first_text_at_ms is None:
                    session.first_text_at_ms = now_ms
                session.latest_text_at_ms = now_ms
                session.event_revision += 1
                if sentence.get("sentence_end"):
                    session.sentence_final_revision += 1
                    session.completed_at_ms = now_ms
                    session.latest_sentence_final_at_ms = now_ms
                    self._provider_sentence_final_counts[session.source_kind] = (
                        self._provider_sentence_final_counts.get(session.source_kind, 0) + 1
                    )
                else:
                    self._partial_counts[session.source_kind] = self._partial_counts.get(session.source_kind, 0) + 1
                session.delivered_revision = session.event_revision
                partial_notification = self._partial_notification(session, combined)
                session.event_condition.notify_all()
            if partial_notification is not None and self._partial_listener is not None:
                try:
                    self._partial_listener(*partial_notification)
                except Exception as exc:
                    self.logger.exception(
                        "realtime_asr.partial_listener_failed",
                        extra={"sourceKind": session.source_kind, "errorCode": exc.__class__.__name__},
                    )

    def _partial_notification(
        self, session: _SourceTaskSession, text: str
    ) -> tuple[AudioFrame, TranscriptResult] | None:
        if self._partial_listener is None or session.latest_frame is None:
            return None
        frame = replace(session.latest_frame, is_final=False)
        return frame, self._result(
            session,
            text=text,
            confidence=0.82,
            first_text_at_ms=session.first_text_at_ms,
            partial_received_at_ms=session.latest_text_at_ms,
            completed_at_ms=None,
            audio_appended_at_ms=session.latest_audio_appended_at_ms,
            commit_sent_at_ms=None,
            lock_wait_at_ms=session.latest_asr_lock_wait_start_at_ms,
            lock_acquired_at_ms=session.latest_asr_lock_acquired_at_ms,
            provider_revision=session.event_revision,
        )

    def _result(
        self,
        session: _SourceTaskSession,
        *,
        text: str,
        confidence: float,
        first_text_at_ms: int | None,
        partial_received_at_ms: int | None,
        completed_at_ms: int | None,
        audio_appended_at_ms: int | None,
        commit_sent_at_ms: int | None,
        lock_wait_at_ms: int | None,
        lock_acquired_at_ms: int | None,
        provider_revision: int | None = None,
    ) -> TranscriptResult:
        return TranscriptResult(
            text=text.strip(),
            confidence=confidence,
            overlap=False,
            usage=AsrUsageReport(
                total_tokens=max(1, len(text.strip()) // 2),
                provider_name=self.settings.realtime_asr_provider,
                model_name=self.settings.realtime_asr_model,
            ),
            first_text_at_ms=first_text_at_ms,
            partial_received_at_ms=partial_received_at_ms,
            completed_at_ms=completed_at_ms,
            audio_appended_at_ms=audio_appended_at_ms,
            first_audio_appended_at_ms=session.first_audio_appended_at_ms,
            commit_sent_at_ms=commit_sent_at_ms,
            asr_lock_wait_start_at_ms=lock_wait_at_ms,
            asr_lock_acquired_at_ms=lock_acquired_at_ms,
            qwen_send_enqueue_at_ms=session.latest_qwen_send_enqueue_at_ms,
            qwen_ws_send_start_at_ms=session.latest_qwen_ws_send_start_at_ms,
            qwen_ws_send_complete_at_ms=session.latest_qwen_ws_send_complete_at_ms,
            provider_revision=provider_revision,
            connection_id=session.connection_id,
        )

    def _close_source_session(self, key: str) -> None:
        with self._source_sessions_lock:
            session = self._source_sessions.pop(key, None)
        if session is not None:
            self._close_detached_session(session)

    def _close_detached_session(self, session: _SourceTaskSession) -> None:
        lifetime_ms = max(0, int((time.monotonic() - session.created_at_monotonic) * 1000))
        source_kind = session.source_kind
        self._connection_closed_counts[source_kind] = self._connection_closed_counts.get(source_kind, 0) + 1
        self._connection_lifetime_total_ms[source_kind] = self._connection_lifetime_total_ms.get(source_kind, 0) + lifetime_ms
        self._connection_lifetime_max_ms[source_kind] = max(
            self._connection_lifetime_max_ms.get(source_kind, 0), lifetime_ms
        )
        self._connection_state_by_source[source_kind] = "closed"
        with session.event_condition:
            session.closed = True
            session.event_condition.notify_all()
        try:
            session.connection.close()
        except Exception:
            pass

    def _connect_url(self) -> str:
        return (
            self.settings.realtime_asr_inference_ws_url.strip()
            or "wss://dashscope.aliyuncs.com/api-ws/v1/inference"
        )

    def _record_error(self, source_kind: str, code: str) -> None:
        self._connection_state_by_source[source_kind] = "error"
        self._last_error_by_source[source_kind] = code

    @staticmethod
    def _provider_error(code: str, detail: str) -> Exception:
        del detail
        normalized = code.lower()
        if any(token in normalized for token in ("accessdenied", "unauthorized", "invalidparameter", "model.notfound")):
            return NonRetryableAsrError(code)
        return RetryableAsrError(code)

    @staticmethod
    def _connection_close_details(exc: Exception) -> tuple[int | None, str | None]:
        received = getattr(exc, "rcvd", None)
        code = getattr(received, "code", None)
        reason = getattr(received, "reason", None)
        return (
            int(code) if isinstance(code, int) else None,
            str(reason)[:256] if reason else None,
        )

    @staticmethod
    def _raise_receiver_error(session: _SourceTaskSession) -> None:
        if session.receiver_error is not None:
            raise session.receiver_error

    @staticmethod
    def _source_session_key(frame: AudioFrame) -> str:
        return f"{frame.session_id}:{frame.source_kind}"

    @staticmethod
    def _normalize_audio_codec(codec: str) -> str:
        normalized = (codec or "").strip().lower().replace("_", "-")
        if normalized in {"pcm", "pcm-s16le", "audio/pcm", "audio/raw", "raw"}:
            return "pcm-s16le"
        return normalized

    @staticmethod
    def _send_audio_chunks(websocket, audio_bytes: bytes) -> tuple[int, int]:
        started_at_ms = int(time.time() * 1000)
        for index in range(0, len(audio_bytes), 6400):
            websocket.send(audio_bytes[index:index + 6400])
        return started_at_ms, int(time.time() * 1000)
