from __future__ import annotations

import base64
import concurrent.futures
import logging
import math
import queue
import random
import re
import threading
from collections import Counter, deque
from dataclasses import replace
from difflib import SequenceMatcher
from time import sleep, time
from typing import Any, Callable
from uuid import uuid4

from app.core.config import Settings
from app.core.errors import DomainRequestError
from app.core.logging import log_event
from app.ports.commercial_hardening import AiUsageRecord, CommercialHardeningRepository
from app.ports.realtime_speech import (
    AccountDesktopDeviceRecord,
    AsrUsageReport,
    AudioFrame,
    DesktopDeviceRecord,
    QuestionCandidateRecord,
    RealtimeFrameReceiptRecord,
    RealtimeAsrGatewayPort,
    RealtimeEvent,
    RealtimePublisherRecord,
    RealtimeSourceKind,
    RealtimeSpeechRepository,
    SessionDesktopBindingRecord,
    TranscriptSegmentRecord,
    TranscriptResult,
    WebSessionHeartbeatRecord,
)
from app.schemas.realtime_speech import (
    DesktopDeviceBindingResponse,
    QuestionCandidateResponse,
    RealtimeFrameReceiptResponse,
    RealtimeEventListResponse,
    RealtimeEventResponse,
    RealtimePublisherResponse,
    RealtimeQuestionCandidateListResponse,
    RealtimeRuntimeCountersResponse,
    RealtimeRuntimePerformanceResponse,
    RealtimeSessionRuntimeResponse,
    RealtimeSessionSnapshotResponse,
    RealtimeStageTimingResponse,
    RealtimeSourceHealthResponse,
    RealtimeTranscriptListResponse,
    TranscriptSegmentResponse,
)
from app.ports.interview_session import InterviewSessionRecord
from app.services.session_service import SessionService
from app.services.billing_service import BillingService, UsageReservationRecord


def _now_ms() -> int:
    return int(time() * 1000)


class RetryableAsrError(Exception):
    pass


class NonRetryableAsrError(Exception):
    pass


class SyntheticRealtimeAsrGateway(RealtimeAsrGatewayPort):
    def __init__(self, settings: Settings) -> None:
        self.settings = settings

    def transcribe(self, *, frame: AudioFrame, attempt: int) -> TranscriptResult:
        try:
            text = frame.audio_bytes.decode("utf-8").strip()
        except UnicodeDecodeError as exc:
            raise NonRetryableAsrError("unreadable_audio_payload") from exc
        if "__asr_retry_once__" in text and attempt == 0:
            raise RetryableAsrError("forced_retryable_asr_failure")
        if "__asr_fail__" in text:
            raise NonRetryableAsrError("forced_permanent_asr_failure")
        low_conf = "__low_conf__" in text
        cleaned = text.replace("__asr_retry_once__", "").replace("__asr_fail__", "").replace("__low_conf__", "").strip() or "（语音内容较短）"
        confidence = 0.72 if low_conf else (0.96 if frame.is_final else 0.78)
        completed_at_ms = _now_ms()
        usage = AsrUsageReport(
            total_tokens=max(1, len(cleaned) // 2),
            provider_name=self.settings.realtime_asr_provider,
            model_name=self.settings.realtime_asr_model,
        )
        return TranscriptResult(
            text=cleaned,
            confidence=confidence,
            overlap=False,
            usage=usage,
            first_text_at_ms=completed_at_ms,
            completed_at_ms=completed_at_ms,
        )

    def warm_session(
        self,
        *,
        session_id: str,
        source_kind: RealtimeSourceKind,
        sample_rate_hz: int = 16_000,
    ) -> None:
        return None

    def close_session(self, *, session_id: str) -> int:
        return 0

    def finalize(self, *, frame: AudioFrame, attempt: int) -> TranscriptResult:
        return self.transcribe(frame=frame, attempt=attempt)

    def close_source(self, *, session_id: str, source_kind: RealtimeSourceKind) -> int:
        return 0


class RealtimeSpeechService:
    def __init__(
        self,
        *,
        settings: Settings,
        logger: logging.Logger,
        repository: RealtimeSpeechRepository,
        session_service: SessionService,
        asr_gateway: RealtimeAsrGatewayPort,
        billing_service: BillingService | None = None,
        commercial_repository: CommercialHardeningRepository | None = None,
        question_prefetcher: Callable[..., object] | None = None,
    ) -> None:
        self.settings = settings
        self.logger = logger
        self.repository = repository
        self.session_service = session_service
        self.asr_gateway = asr_gateway
        self.billing_service = billing_service
        self.commercial_repository = commercial_repository
        self.question_prefetcher = question_prefetcher
        self._asr_executor = concurrent.futures.ThreadPoolExecutor(
            max_workers=max(2, settings.realtime_asr_worker_count),
            thread_name_prefix="realtime-asr",
        )
        self._cold_executor = concurrent.futures.ThreadPoolExecutor(
            max_workers=max(1, settings.realtime_cold_path_worker_count),
            thread_name_prefix="realtime-cold",
        )
        self._asr_slots = threading.BoundedSemaphore(max(4, settings.realtime_asr_worker_count * 2))
        self._cold_slots = threading.BoundedSemaphore(max(8, settings.realtime_cold_path_queue_max))
        self._latest_timings_by_session_source: dict[tuple[str, RealtimeSourceKind], dict[str, object]] = {}
        self._counters_by_session_source: dict[tuple[str, RealtimeSourceKind], dict[str, int | float]] = {}
        self._active_requests_by_session_source: dict[tuple[str, RealtimeSourceKind], int] = {}
        self._frame_worker_lock = threading.Lock()
        self._frame_workers: dict[tuple[str, RealtimeSourceKind], threading.Thread] = {}
        self._frame_queues: dict[tuple[str, RealtimeSourceKind], "queue.Queue[dict[str, object]]"] = {}
        self._retired_session_ids: set[str] = set()
        self._delivery_metric_counts: Counter[str] = Counter()
        self._delivery_metric_latest_ms: dict[str, int] = {}
        self._terminal_lock = threading.Lock()
        self._accepted_terminal_ids: dict[tuple[str, RealtimeSourceKind], dict[str, int]] = {}
        self._latest_source_generations: dict[tuple[str, RealtimeSourceKind], int] = {}
        self._watchdog_lock = threading.Lock()
        self._active_source_turns: dict[tuple[str, RealtimeSourceKind], dict[str, object]] = {}
        self._watchdog_thread: threading.Thread | None = None
        self._capture_control_cache: dict[str, str] = {}
        self._publisher_status_cache: dict[str, str] = {}
        self._stable_question_state: dict[tuple[str, str], dict[str, object]] = {}
        self._trace_lock = threading.Lock()
        self._trace_records: dict[str, dict[str, object]] = {}
        self._trace_order: deque[str] = deque(maxlen=4096)
        self._queue_wait_samples: dict[tuple[str, RealtimeSourceKind], deque[int]] = {}
        self._provider_partial_publish_lock = threading.Lock()
        self._meter_lock = threading.Lock()
        self._meter_stops: dict[str, threading.Event] = {}
        self._meter_threads: dict[str, threading.Thread] = {}
        partial_listener_setter = getattr(self.asr_gateway, "set_partial_listener", None)
        if callable(partial_listener_setter):
            partial_listener_setter(self._publish_provider_partial)

    def start_live_session(self, *, user_id: str, session_id: str) -> InterviewSessionRecord:
        """Start one commercial interview, charge its first minute and prewarm ASR."""
        reservation = self._reserve_realtime_minute(
            user_id=user_id,
            session_id=session_id,
            minute_index=0,
        )
        if reservation is not None and reservation.status == "insufficient_balance":
            raise DomainRequestError(
                "billing",
                "realtime-minute",
                "积分不足，实时面试每分钟需要 5 点，请充值或购买会员后重试。",
                402,
                error_code="realtime_minute_insufficient_balance",
            )
        try:
            session = self.session_service.start_session(user_id=user_id, session_id=session_id)
        except Exception:
            if reservation is not None and reservation.status == "reserved":
                self.billing_service.release_usage(usage_id=reservation.usage_id)  # type: ignore[union-attr]
            raise
        if reservation is not None and reservation.status == "reserved":
            self.billing_service.settle_usage(usage_id=reservation.usage_id)  # type: ignore[union-attr]
        self._capture_control_cache[session_id] = "capturing"
        self._ensure_realtime_metering(user_id=user_id, session_id=session_id)
        self._prewarm_asr_session(session_id=session_id)
        return session

    def _realtime_minute_usage_id(self, *, session_id: str, minute_index: int) -> str:
        return f"realtime-minute:{session_id}:{max(0, minute_index)}"

    def _reserve_realtime_minute(
        self,
        *,
        user_id: str,
        session_id: str,
        minute_index: int,
    ) -> UsageReservationRecord | None:
        if self.billing_service is None:
            return None
        return self.billing_service.reserve_usage(
            user_id=user_id,
            usage_id=self._realtime_minute_usage_id(session_id=session_id, minute_index=minute_index),
            usage_kind="realtime_minute",
        )

    def _settle_realtime_minute(
        self,
        *,
        user_id: str,
        session_id: str,
        observed_at_ms: int | None = None,
    ) -> bool:
        if self.billing_service is None:
            return True
        session = self.session_service.get_session(user_id=user_id, session_id=session_id)
        if session.status != "live" or session.started_at_ms is None:
            return False
        now_ms = observed_at_ms or _now_ms()
        minute_index = max(0, (now_ms - session.started_at_ms) // 60_000)
        reservation = self._reserve_realtime_minute(
            user_id=user_id,
            session_id=session_id,
            minute_index=minute_index,
        )
        if reservation is None:
            return True
        if reservation.status == "insufficient_balance":
            self._pause_for_insufficient_realtime_balance(user_id=user_id, session_id=session_id)
            return False
        if reservation.status == "reserved":
            self.billing_service.settle_usage(usage_id=reservation.usage_id)
        return True

    def _ensure_realtime_metering(self, *, user_id: str, session_id: str) -> None:
        if self.billing_service is None:
            return
        with self._meter_lock:
            current = self._meter_threads.get(session_id)
            if current is not None and current.is_alive():
                return
            stop_event = threading.Event()
            worker = threading.Thread(
                target=self._realtime_meter_loop,
                kwargs={"user_id": user_id, "session_id": session_id, "stop_event": stop_event},
                name=f"realtime-meter-{session_id[-8:]}",
                daemon=True,
            )
            self._meter_stops[session_id] = stop_event
            self._meter_threads[session_id] = worker
            worker.start()

    def _realtime_meter_loop(
        self,
        *,
        user_id: str,
        session_id: str,
        stop_event: threading.Event,
    ) -> None:
        try:
            while not stop_event.is_set():
                try:
                    session = self.session_service.get_session(user_id=user_id, session_id=session_id)
                except Exception:
                    return
                if session.status != "live":
                    return
                if self.capture_control_state(session_id=session_id) == "capturing":
                    if not self._settle_realtime_minute(user_id=user_id, session_id=session_id):
                        return
                now_ms = _now_ms()
                next_boundary_ms = (
                    ((now_ms - (session.started_at_ms or now_ms)) // 60_000 + 1) * 60_000
                    + (session.started_at_ms or now_ms)
                )
                # Sleep directly to the next billing boundary. The stop event
                # still wakes immediately on pause/end, so metering adds no
                # periodic database polling to the realtime hot path.
                stop_event.wait(timeout=max(1.0, (next_boundary_ms - now_ms) / 1000))
        finally:
            with self._meter_lock:
                if self._meter_stops.get(session_id) is stop_event:
                    self._meter_stops.pop(session_id, None)
                    self._meter_threads.pop(session_id, None)

    def _stop_realtime_metering(self, *, session_id: str) -> None:
        with self._meter_lock:
            stop_event = self._meter_stops.pop(session_id, None)
            self._meter_threads.pop(session_id, None)
        if stop_event is not None:
            stop_event.set()

    def _prewarm_asr_session(self, *, session_id: str) -> None:
        if not self.settings.realtime_asr_prewarm_enabled:
            return
        warm_session = getattr(self.asr_gateway, "warm_session", None)
        if not callable(warm_session):
            return
        for source_kind in ("microphone", "system"):
            future = self._asr_executor.submit(
                warm_session,
                session_id=session_id,
                source_kind=source_kind,
                sample_rate_hz=16_000,
            )
            future.add_done_callback(
                lambda completed, kind=source_kind: self._observe_asr_prewarm(
                    completed,
                    session_id=session_id,
                    source_kind=kind,
                )
            )

    def _observe_asr_prewarm(
        self,
        future: concurrent.futures.Future[object],
        *,
        session_id: str,
        source_kind: str,
    ) -> None:
        try:
            future.result()
        except Exception as exc:
            self._log(
                logging.WARNING,
                "realtime_speech.asr_prewarm_failed",
                session_id=session_id,
                publisher_id=None,
                state="prewarm-failed",
                error_code=exc.__class__.__name__,
            )
            return
        self._log(
            logging.INFO,
            "realtime_speech.asr_prewarm_ready",
            session_id=session_id,
            publisher_id=None,
            state=f"{source_kind}-ready",
        )

    def _pause_for_insufficient_realtime_balance(self, *, user_id: str, session_id: str) -> None:
        if self.capture_control_state(session_id=session_id) != "paused":
            self._save_event(
                session_id=session_id,
                owner_user_id=user_id,
                kind="capture-control",
                payload={
                    "action": "pause",
                    "captureState": "paused",
                    "reason": "realtime-minute-insufficient-balance",
                },
            )
            self._save_event(
                session_id=session_id,
                owner_user_id=user_id,
                kind="degraded",
                payload={
                    "reason": "realtime-minute-insufficient-balance",
                    "message": "积分不足，实时收音已暂停。",
                },
            )
        self._capture_control_cache[session_id] = "paused"
        self.asr_gateway.close_session(session_id=session_id)

    def _publish_provider_partial(self, frame: AudioFrame, result: TranscriptResult) -> None:
        """Publish Qwen partials directly from its receive pump.

        This deliberately bypasses the audio append worker: provider receive,
        Redis XADD and SSE consumption form their own monotonic event path.
        Stable-question detection remains a downstream observer and never gates
        the subtitle event.
        """
        if frame.session_id in self._retired_session_ids or not result.text.strip():
            return
        publisher = self.repository.get_publisher(frame.publisher_id)
        if publisher is None or publisher.status in {"closed", "failed"}:
            return
        if self.capture_control_state(session_id=frame.session_id) == "paused":
            return
        partial_received_at_ms = result.partial_received_at_ms or _now_ms()
        partial_trace_id = (
            f"{frame.trace_id}:p{result.provider_revision}"
            if frame.trace_id and result.provider_revision is not None
            else frame.trace_id
        )
        with self._provider_partial_publish_lock:
            suppression_reason = self._suppression_reason(result.text, frame=frame)
            if suppression_reason is None:
                suppression_reason = self._duplicate_nearby_suppression_reason(
                    text=result.text,
                    publisher=publisher,
                    frame=frame,
                )
            if suppression_reason is not None:
                return
            current = self.repository.get_transcript(frame.session_id, frame.segment_id)
            if current is not None and current.is_final:
                return
            published_at_ms = _now_ms()
            first_partial = current is None
            first_partial_at_ms = (
                partial_received_at_ms
                if first_partial
                else int((current.performance or {}).get("systemFirstEffectivePartialAtMs") or partial_received_at_ms)
            )
            timing = {
                **{
                    key: value
                    for key, value in frame.diagnostics.items()
                    if value is None or isinstance(value, (str, int, float, bool))
                },
                "traceId": partial_trace_id,
                "sourceFrameTraceId": frame.trace_id,
                "sessionId": frame.session_id,
                "channel": frame.source_kind,
                "sequence": frame.sequence,
                "revision": frame.revision,
                "utteranceId": frame.segment_id,
                "captureToSendMs": (
                    max(0, frame.sent_at_ms - frame.captured_at_ms) if frame.sent_at_ms is not None else None
                ),
                "sendToIngestMs": (
                    max(0, frame.backend_received_at_ms - frame.sent_at_ms)
                    if frame.backend_received_at_ms is not None and frame.sent_at_ms is not None else None
                ),
                "captureToIngestMs": (
                    max(0, frame.backend_received_at_ms - frame.captured_at_ms)
                    if frame.backend_received_at_ms is not None else None
                ),
                "queueWaitMs": 0,
                "asrTtftMs": (
                    max(0, partial_received_at_ms - result.audio_appended_at_ms)
                    if result.audio_appended_at_ms is not None else None
                ),
                "finalTranscriptMs": None,
                "stopToTerminalMs": None,
                "backendPushMs": max(0, published_at_ms - partial_received_at_ms),
                "captureToPublishMs": max(0, published_at_ms - frame.captured_at_ms),
                "frontendRenderMs": None,
                "speechStartAtMs": frame.vad_triggered_at_ms or frame.started_at_ms,
                "systemVadTriggerAtMs": frame.vad_triggered_at_ms if frame.source_kind == "system" else None,
                "systemSpeechStartAtMs": frame.speech_confirmed_at_ms if frame.source_kind == "system" else None,
                "systemFirstEffectivePartialAtMs": first_partial_at_ms if frame.source_kind == "system" else None,
                "framesBeforeFirstPartial": (
                    frame.revision if first_partial else (current.performance or {}).get("framesBeforeFirstPartial")
                ),
                "desktopAudioCaptureAtMs": frame.captured_at_ms,
                "desktopWsSendAtMs": frame.sent_at_ms,
                "backendWsReceiveAtMs": frame.backend_received_at_ms,
                "queueEnterAtMs": frame.backend_received_at_ms,
                "queueLeaveAtMs": frame.backend_received_at_ms,
                "qwenAudioAppendAtMs": result.audio_appended_at_ms,
                "qwenPartialReceivedAtMs": partial_received_at_ms,
                "qwenFinalReceivedAtMs": None,
                "providerResultReceivedAtMs": partial_received_at_ms,
                "redisEventXaddAtMs": None,
                "redisEventXreadAtMs": None,
                "sseEventSendAtMs": None,
                "browserEventReceiveAtMs": None,
                "browserStateUpdateAtMs": None,
                "browserRenderAtMs": None,
                "speechEndDetectedAtMs": None,
                "manualCommitSentAtMs": None,
                "asrSessionLockWaitStartAtMs": result.asr_lock_wait_start_at_ms,
                "asrSessionLockAcquiredAtMs": result.asr_lock_acquired_at_ms,
                "qwenSendEnqueueAtMs": result.qwen_send_enqueue_at_ms,
                "qwenWsSendStartAtMs": result.qwen_ws_send_start_at_ms,
                "qwenWsSendCompleteAtMs": result.qwen_ws_send_complete_at_ms,
                "providerRevision": result.provider_revision,
                "partialTextLength": len(result.text.strip()),
                "connectionId": result.connection_id,
            }
            transcript = self.repository.save_transcript(TranscriptSegmentRecord(
                segment_id=frame.segment_id,
                session_id=frame.session_id,
                owner_user_id=publisher.owner_user_id,
                source_id=frame.source_id,
                source_kind=frame.source_kind,
                role="candidate" if frame.source_kind == "microphone" else "interviewer",
                revision=max(frame.revision, current.revision + 1 if current is not None else frame.revision),
                text=result.text.strip(),
                transcript_confidence=result.confidence,
                started_at_ms=frame.started_at_ms,
                ended_at_ms=frame.ended_at_ms,
                is_final=False,
                overlap=result.overlap,
                created_at_ms=current.created_at_ms if current is not None else published_at_ms,
                published_at_ms=published_at_ms,
                performance=timing,
                usage=result.usage,
            ))
            timing = {
                **timing,
                "revision": transcript.revision,
                "providerRevision": result.provider_revision,
                "segmentId": transcript.segment_id,
                "utteranceId": transcript.segment_id,
                "textLength": len(transcript.text),
                "transcriptEventCreatedAtMs": _now_ms(),
            }
            event = self._save_event(
                session_id=frame.session_id,
                owner_user_id=publisher.owner_user_id,
                kind="transcript-updated",
                payload={
                    "segmentId": transcript.segment_id,
                    "sourceId": transcript.source_id,
                    "sourceKind": transcript.source_kind,
                    "revision": transcript.revision,
                    "role": transcript.role,
                    "text": transcript.text,
                    "transcriptConfidence": transcript.transcript_confidence,
                    "startedAtMs": transcript.started_at_ms,
                    "endedAtMs": transcript.ended_at_ms,
                    "isFinal": False,
                    "overlap": transcript.overlap,
                    "terminalState": None,
                    "finalizationReason": None,
                    "publishedAtMs": published_at_ms,
                    "performance": timing,
                },
            )
            event_performance = event.payload.get("performance")
            if isinstance(event_performance, dict):
                timing = dict(event_performance)
            self._observe_trace(partial_trace_id, **timing)
            self._set_latest_timing(session_id=frame.session_id, source_kind=frame.source_kind, timing=timing)
            # Stable/question-prefetch is deliberately after the subtitle XADD.
            self._observe_stable_interviewer_partial(transcript)

    def _submit_cold(self, operation, /, *args, **kwargs) -> None:
        """Run optional persistence/metrics outside the realtime publication path."""
        if not self._cold_slots.acquire(blocking=False):
            self.logger.warning("realtime_speech.cold_path_queue_full")
            return
        try:
            future = self._cold_executor.submit(operation, *args, **kwargs)
            future.add_done_callback(lambda _future: self._cold_slots.release())
        except RuntimeError:
            self._cold_slots.release()
            self.logger.warning("realtime_speech.cold_path_rejected")

    def _transition_publisher_status(self, publisher: RealtimePublisherRecord, status: str) -> RealtimePublisherRecord:
        current = self._publisher_status_cache.get(publisher.publisher_id, publisher.status)
        if current == status:
            return publisher if publisher.status == status else replace(publisher, status=status)
        updated = self.repository.save_publisher(replace(publisher, status=status))
        self._publisher_status_cache[publisher.publisher_id] = status
        return updated

    def _observe_stable_interviewer_partial(self, transcript: TranscriptSegmentRecord) -> RealtimeEvent | None:
        if transcript.source_kind != "system" or not self._is_meaningful_transcript(transcript.text):
            return None
        key = (transcript.session_id, transcript.segment_id)
        previous = self._stable_question_state.get(key)
        previous_text = str(previous.get("text", "")) if previous else ""
        current_text = transcript.text.strip()
        if transcript.is_final:
            stable_text = current_text
        elif previous_text and current_text.startswith(previous_text):
            stable_text = previous_text
        else:
            prefix_length = 0
            for left, right in zip(previous_text, current_text):
                if left != right:
                    break
                prefix_length += 1
            stable_text = current_text[:prefix_length].rstrip("，。！？、；：,.!?;: ")
        previous_stable = str(previous.get("stableText", "")) if previous else ""
        self._stable_question_state[key] = {
            "text": current_text,
            "stableText": stable_text or previous_stable,
            "revision": transcript.revision,
            "updatedAtMs": _now_ms(),
        }
        if len(self._stable_question_state) > 256:
            oldest = min(self._stable_question_state, key=lambda item: int(self._stable_question_state[item].get("updatedAtMs", 0)))
            self._stable_question_state.pop(oldest, None)
        if len(stable_text) < 4 or stable_text == previous_stable:
            return None
        question_id = f"question:{transcript.session_id}:{transcript.segment_id}"
        event = self._save_event(
            session_id=transcript.session_id,
            owner_user_id=transcript.owner_user_id,
            kind="question-stable",
            payload={
                "questionId": question_id,
                "questionRevision": transcript.revision,
                "questionText": stable_text,
                "sourceSegmentId": transcript.segment_id,
            },
        )
        if self.question_prefetcher is not None:
            self._submit_cold(
                self.question_prefetcher,
                user_id=transcript.owner_user_id,
                session_id=transcript.session_id,
                question_id=question_id,
                revision=transcript.revision,
                question=stable_text,
            )
        return event

    def _record_speech_usage(
        self,
        *,
        publisher: RealtimePublisherRecord,
        frame: AudioFrame,
        result: TranscriptResult | None,
        final_latency_ms: int | None,
        safe_error_code: str | None = None,
    ) -> None:
        if self.commercial_repository is None or not frame.is_final:
            return
        try:
            usage = result.usage if result is not None else None
            self.commercial_repository.record_ai_usage(AiUsageRecord(
                usage_id=f"ai-speech:{frame.session_id}:{frame.segment_id}:{frame.revision}",
                owner_user_id=publisher.owner_user_id,
                operation_kind="speech",
                provider=usage.provider_name if usage is not None else "dashscope-realtime-asr",
                model=usage.model_name if usage is not None else self.settings.realtime_asr_model,
                status="succeeded" if safe_error_code is None else "failed",
                related_task_id=frame.segment_id,
                session_id=frame.session_id,
                total_units=usage.total_tokens if usage is not None else None,
                duration_ms=final_latency_ms,
                final_latency_ms=final_latency_ms,
                safe_error_code=safe_error_code,
                created_at_ms=_now_ms(),
            ))
        except Exception as exc:  # Observability must never interrupt live transcription.
            self.logger.warning("realtime_speech.ai_usage_record_failed", extra={"segment_id": frame.segment_id, "safe_error_code": exc.__class__.__name__})

    @staticmethod
    def _session_source_key(session_id: str, source_kind: RealtimeSourceKind) -> tuple[str, RealtimeSourceKind]:
        return (session_id, source_kind)

    def _counter_bucket(self, *, session_id: str, source_kind: RealtimeSourceKind) -> dict[str, int | float]:
        key = self._session_source_key(session_id, source_kind)
        return self._counters_by_session_source.setdefault(key, {
            "queueDepth": 0,
            "droppedPartialUpdates": 0,
            "connectionRecreations": 0,
            "emptyResultsSuppressed": 0,
            "phantomResultsSuppressed": 0,
            "repetitiveResultsSuppressed": 0,
            "duplicateResultsSuppressed": 0,
            "fillerResultsSuppressed": 0,
            "chunksProduced": 0,
            "chunksUploaded": 0,
            "framesConsumed": 0,
            "serializedAudioBytes": 0,
            "terminalAdmissions": 0,
            "terminalDuplicates": 0,
            "terminalAdmissionFailures": 0,
            "terminalResends": 0,
            "incompleteRecoveries": 0,
            "sourceReconnects": 0,
        })

    def _set_latest_timing(self, *, session_id: str, source_kind: RealtimeSourceKind, timing: dict[str, object]) -> None:
        self._latest_timings_by_session_source[self._session_source_key(session_id, source_kind)] = timing

    def _latest_timing(self, *, session_id: str, source_kind: RealtimeSourceKind) -> dict[str, object] | None:
        return self._latest_timings_by_session_source.get(self._session_source_key(session_id, source_kind))

    def _active_request_enter(self, *, session_id: str, source_kind: RealtimeSourceKind) -> int:
        key = self._session_source_key(session_id, source_kind)
        next_depth = self._active_requests_by_session_source.get(key, 0) + 1
        self._active_requests_by_session_source[key] = next_depth
        self._counter_bucket(session_id=session_id, source_kind=source_kind)["queueDepth"] = max(0, next_depth - 1)
        return next_depth

    def _active_request_leave(self, *, session_id: str, source_kind: RealtimeSourceKind) -> None:
        key = self._session_source_key(session_id, source_kind)
        remaining = max(0, self._active_requests_by_session_source.get(key, 0) - 1)
        if remaining == 0:
            self._active_requests_by_session_source.pop(key, None)
        else:
            self._active_requests_by_session_source[key] = remaining
        self._counter_bucket(session_id=session_id, source_kind=source_kind)["queueDepth"] = max(0, remaining - 1)

    def _gateway_diagnostics(self, *, source_kind: RealtimeSourceKind) -> dict[str, int | float]:
        diagnostics = getattr(self.asr_gateway, "diagnostics", None)
        if callable(diagnostics):
            payload = diagnostics(source_kind)
            if isinstance(payload, dict):
                return {
                    str(key): value
                    for key, value in payload.items()
                    if isinstance(value, (int, float)) and not isinstance(value, bool)
                }
        return {}

    def _gateway_runtime_status(self, *, source_kind: RealtimeSourceKind) -> dict[str, object]:
        runtime_status = getattr(self.asr_gateway, "runtime_status", None)
        if callable(runtime_status):
            payload = runtime_status(source_kind)
            if isinstance(payload, dict):
                return dict(payload)
        return {}

    def operational_metrics(self) -> dict[str, object]:
        import os
        import resource

        descriptor_root = "/proc/self/fd" if os.path.isdir("/proc/self/fd") else "/dev/fd"
        try:
            file_descriptors = len(os.listdir(descriptor_root))
        except OSError:
            file_descriptors = -1
        usage = resource.getrusage(resource.RUSAGE_SELF)
        repository_diagnostics = getattr(self.repository, "operational_diagnostics", None)
        queue_channels: dict[str, dict[str, int]] = {}
        for (session_id, source_kind), work_queue in self._frame_queues.items():
            counter = self._counter_bucket(session_id=session_id, source_kind=source_kind)
            oldest_age_ms = 0
            with work_queue.mutex:
                if work_queue.queue:
                    queued_at = work_queue.queue[0].get("queue_enter_at_ms")
                    if isinstance(queued_at, int):
                        oldest_age_ms = max(0, _now_ms() - queued_at)
            waits = list(self._queue_wait_samples.get((session_id, source_kind), ()))
            queue_channels[f"{session_id}:{source_kind}"] = {
                "depth": work_queue.qsize(),
                "oldestFrameAgeMs": oldest_age_ms,
                "latestQueueWaitMs": waits[-1] if waits else 0,
                "framesIn": int(counter.get("chunksProduced", 0)),
                "framesOut": int(counter.get("framesConsumed", 0)),
            }
        queues = {key: value["depth"] for key, value in queue_channels.items()}
        return {
            "activeQueueWorkers": sum(1 for worker in self._frame_workers.values() if worker.is_alive()),
            "queueDepthByChannel": queues,
            "queuedFrames": sum(queues.values()),
            "queueByChannel": queue_channels,
            "fileDescriptors": file_descriptors,
            "maxResidentSetKb": int(usage.ru_maxrss),
            "asr": {
                source_kind: self._gateway_diagnostics(source_kind=source_kind)  # type: ignore[arg-type]
                for source_kind in ("microphone", "system")
            },
            "rawAudioPersisted": False,
            "delivery": {
                "counts": dict(self._delivery_metric_counts),
                "latestDurationMs": dict(self._delivery_metric_latest_ms),
            },
            "eventStore": repository_diagnostics() if callable(repository_diagnostics) else {},
            "traceSummary": self.performance_summary(),
        }

    @staticmethod
    def _percentile(values: list[int], fraction: float) -> int | None:
        if not values:
            return None
        ordered = sorted(values)
        index = min(len(ordered) - 1, max(0, int((len(ordered) - 1) * fraction + 0.999999)))
        return ordered[index]

    def _observe_trace(self, trace_id: str | None, **fields: object) -> None:
        if not trace_id:
            return
        safe_fields = {
            key: value
            for key, value in fields.items()
            if value is None
            or isinstance(value, (str, int, bool))
            or (isinstance(value, float) and math.isfinite(value))
        }
        with self._trace_lock:
            if trace_id not in self._trace_records:
                if len(self._trace_order) == self._trace_order.maxlen:
                    expired = self._trace_order.popleft()
                    self._trace_records.pop(expired, None)
                self._trace_order.append(trace_id)
                self._trace_records[trace_id] = {"traceId": trace_id}
            self._trace_records[trace_id].update(safe_fields)

    def _trace_snapshot(self, trace_id: str | None) -> dict[str, object]:
        if not trace_id:
            return {}
        with self._trace_lock:
            return dict(self._trace_records.get(trace_id, {}))

    def observe_sse_delivery(self, events: list[RealtimeEvent], *, sent_at_ms: int) -> list[RealtimeEvent]:
        delivered: list[RealtimeEvent] = []
        for event in events:
            performance = event.payload.get("performance")
            if not isinstance(performance, dict):
                delivered.append(event)
                continue
            trace_id = performance.get("traceId")
            trace = self._trace_snapshot(str(trace_id) if trace_id else None)
            enriched_performance = {
                **performance,
                **{
                    key: value
                    for key, value in trace.items()
                    if key != "traceId" and (value is None or isinstance(value, (str, int, float, bool)))
                },
                "sseGeneratorYieldAtMs": sent_at_ms,
                "sseEventSendAtMs": sent_at_ms,
                "httpResponseChunkWrittenAvailable": False,
                "eventId": event.event_id,
            }
            enriched = replace(event, payload={**event.payload, "performance": enriched_performance})
            delivered.append(enriched)
            self._observe_trace(
                str(trace_id) if trace_id else None,
                redisEventXreadAtMs=performance.get("redisEventXreadAtMs"),
                redisReadMode=performance.get("redisReadMode"),
                sseGeneratorYieldAtMs=sent_at_ms,
                sseEventSendAtMs=sent_at_ms,
                httpResponseChunkWrittenAvailable=False,
                eventId=event.event_id,
            )
        return delivered

    def performance_summary(self, *, session_id: str | None = None) -> dict[str, object]:
        with self._trace_lock:
            records = [dict(item) for item in self._trace_records.values() if session_id is None or item.get("sessionId") == session_id]
        pairs = {
            "desktopVadToWorkletMs": ("desktopVadConfirmAtMs", "desktopAudioWorkletOutputAtMs"),
            "desktopWorkletToRendererMs": ("desktopAudioWorkletOutputAtMs", "desktopRendererReceiveAtMs"),
            "desktopRendererToPcmMs": ("desktopRendererReceiveAtMs", "desktopPcmConversionAtMs"),
            "desktopPcmToRingBufferMs": ("desktopPcmConversionAtMs", "desktopRingBufferWriteAtMs"),
            "desktopRingBufferToEnqueueMs": ("desktopRingBufferWriteAtMs", "desktopPublisherEnqueueAtMs"),
            "desktopEnqueueToFlushMs": ("desktopPublisherEnqueueAtMs", "desktopPublisherFlushAtMs"),
            "desktopFlushToWsSendMs": ("desktopPublisherFlushAtMs", "desktopWsSendAtMs"),
            "backendWsToValidationMs": ("backendWebsocketFrameReceivedAtMs", "backendFrameValidationDoneAtMs"),
            "backendValidationToRoutingMs": ("backendFrameValidationDoneAtMs", "backendChannelRoutingDoneAtMs"),
            "backendRoutingToQueueMs": ("backendChannelRoutingDoneAtMs", "queueEnterAtMs"),
            "backendQueueMs": ("queueEnterAtMs", "queueLeaveAtMs"),
            "backendWorkerToLockWaitMs": ("queueLeaveAtMs", "asrSessionLockWaitStartAtMs"),
            "backendAsrLockWaitMs": ("asrSessionLockWaitStartAtMs", "asrSessionLockAcquiredAtMs"),
            "backendLockToQwenEnqueueMs": ("asrSessionLockAcquiredAtMs", "qwenSendEnqueueAtMs"),
            "backendQwenEnqueueToWsSendMs": ("qwenSendEnqueueAtMs", "qwenWsSendStartAtMs"),
            "backendQwenWsSendMs": ("qwenWsSendStartAtMs", "qwenWsSendCompleteAtMs"),
            "speechStartToFirstFrameSendMs": ("speechStartAtMs", "desktopWsSendAtMs"),
            "firstFrameToQwenAppendMs": ("desktopWsSendAtMs", "qwenAudioAppendAtMs"),
            "networkMs": ("desktopWsSendAtMs", "backendWsReceiveAtMs"),
            "preprocessMs": ("backendWsReceiveAtMs", "queueEnterAtMs"),
            "queueWaitMs": ("queueEnterAtMs", "queueLeaveAtMs"),
            "asrInputLagMs": ("queueLeaveAtMs", "qwenAudioAppendAtMs"),
            "qwenPartialMs": ("qwenAudioAppendAtMs", "qwenPartialReceivedAtMs"),
            "revisionQwenToEventMs": ("qwenPartialReceivedAtMs", "transcriptEventCreatedAtMs"),
            "revisionEventToRedisXaddStartMs": ("transcriptEventCreatedAtMs", "redisEventXaddStartAtMs"),
            "revisionRedisXaddMs": ("redisEventXaddStartAtMs", "redisEventXaddCompleteAtMs"),
            "revisionRedisToSseMs": ("redisEventXaddCompleteAtMs", "sseGeneratorYieldAtMs"),
            "revisionSseToBrowserChunkMs": ("sseGeneratorYieldAtMs", "browserStreamChunkReceivedAtMs"),
            "revisionBrowserChunkToParseMs": ("browserStreamChunkReceivedAtMs", "browserEventParsedAtMs"),
            "revisionBrowserParseToStoreStartMs": ("browserEventParsedAtMs", "transcriptStoreUpdateStartAtMs"),
            "revisionStoreUpdateMs": ("transcriptStoreUpdateStartAtMs", "transcriptStoreUpdateCompleteAtMs"),
            "revisionStoreToReactRenderMs": ("transcriptStoreUpdateCompleteAtMs", "reactRenderStartAtMs"),
            "revisionReactRenderToCommitMs": ("reactRenderStartAtMs", "reactCommitAtMs"),
            "revisionReactCommitToPaintMs": ("reactCommitAtMs", "browserPaintAtMs"),
            "revisionQwenToPaintMs": ("qwenPartialReceivedAtMs", "browserPaintAtMs"),
            "qwenPartialToRedisXaddMs": ("qwenPartialReceivedAtMs", "redisEventXaddAtMs"),
            "redisXaddToXreadMs": ("redisEventXaddAtMs", "redisEventXreadAtMs"),
            "redisXreadToSseSendMs": ("redisEventXreadAtMs", "sseEventSendAtMs"),
            "sseDeliveryMs": ("sseEventSendAtMs", "browserEventReceiveAtMs"),
            "browserStateUpdateMs": ("browserEventReceiveAtMs", "browserStateUpdateAtMs"),
            "browserRenderMs": ("browserEventReceiveAtMs", "browserRenderAtMs"),
            "browserStateToReactRenderMs": ("browserStateUpdateAtMs", "browserRenderAtMs"),
            "endToEndPartialMs": ("desktopAudioCaptureAtMs", "browserRenderAtMs"),
            "speechStartToBrowserFirstPartialMs": ("speechStartAtMs", "browserRenderAtMs"),
            "speechEndToCommitMs": ("speechEndDetectedAtMs", "manualCommitSentAtMs"),
            "commitToFinalMs": ("manualCommitSentAtMs", "qwenFinalReceivedAtMs"),
            "speechEndToFinalMs": ("speechEndDetectedAtMs", "qwenFinalReceivedAtMs"),
        }
        distributions: dict[str, object] = {}
        utterance_groups: dict[tuple[object, object, object], list[dict[str, object]]] = {}
        for item in records:
            key = (item.get("sessionId"), item.get("channel"), item.get("utteranceId"))
            if key[2] is not None:
                utterance_groups.setdefault(key, []).append(item)
        for name, (start_key, end_key) in pairs.items():
            if name in {
                "speechStartToFirstFrameSendMs",
                "firstFrameToQwenAppendMs",
                "qwenPartialMs",
                "speechStartToBrowserFirstPartialMs",
            }:
                samples = []
                for group in utterance_groups.values():
                    starts = [int(item[start_key]) for item in group if isinstance(item.get(start_key), int)]
                    ends = [int(item[end_key]) for item in group if isinstance(item.get(end_key), int)]
                    if starts and ends and min(ends) >= min(starts):
                        samples.append(min(ends) - min(starts))
            else:
                samples = [int(item[end_key]) - int(item[start_key]) for item in records if isinstance(item.get(start_key), int) and isinstance(item.get(end_key), int) and int(item[end_key]) >= int(item[start_key])]
            distributions[name] = {
                "count": len(samples),
                "p50": self._percentile(samples, 0.50),
                "p95": self._percentile(samples, 0.95),
                "p99": self._percentile(samples, 0.99),
                "max": max(samples) if samples else None,
            }
        revision_stages = {
            "qwen": "qwenPartialReceivedAtMs",
            "event": "transcriptEventCreatedAtMs",
            "redisXadd": "redisEventXaddCompleteAtMs",
            "redisXread": "redisEventXreadAtMs",
            "sse": "sseGeneratorYieldAtMs",
            "browser": "browserEventParsedAtMs",
            "store": "transcriptStoreUpdateCompleteAtMs",
            "reactCommit": "reactCommitAtMs",
            "paint": "browserPaintAtMs",
        }
        visible_records = [item for item in records if item.get("visibilityState") == "visible"]
        stage_counts = {
            stage: sum(1 for item in records if isinstance(item.get(field), int))
            for stage, field in revision_stages.items()
        }
        visible_stage_counts = {
            stage: sum(1 for item in visible_records if isinstance(item.get(field), int))
            for stage, field in revision_stages.items()
        }
        revision_gaps: dict[str, object] = {}
        browser_stages = {"browser", "store", "reactCommit", "paint"}
        for stage, field in revision_stages.items():
            gaps: list[int] = []
            anomalies: list[dict[str, object]] = []
            for (group_session, group_channel, group_utterance), group in utterance_groups.items():
                ordered = sorted(
                    (
                        item for item in group
                        if isinstance(item.get(field), int)
                        and (stage not in browser_stages or item.get("visibilityState") == "visible")
                    ),
                    key=lambda item: (int(item.get("providerRevision") or item.get("revision") or 0), int(item[field])),
                )
                for previous, current in zip(ordered, ordered[1:]):
                    gap = int(current[field]) - int(previous[field])
                    if gap < 0:
                        continue
                    gaps.append(gap)
                    if gap > 500:
                        anomalies.append({
                            "sessionId": group_session,
                            "channel": group_channel,
                            "utteranceId": group_utterance,
                            "fromRevision": previous.get("providerRevision") or previous.get("revision"),
                            "toRevision": current.get("providerRevision") or current.get("revision"),
                            "gapMs": gap,
                            "threshold": 3000 if gap > 3000 else 1000 if gap > 1000 else 500,
                        })
            revision_gaps[stage] = {
                "count": len(gaps),
                "p50": self._percentile(gaps, 0.50),
                "p95": self._percentile(gaps, 0.95),
                "p99": self._percentile(gaps, 0.99),
                "max": max(gaps) if gaps else None,
                "over500Ms": sum(1 for gap in gaps if gap > 500),
                "over1000Ms": sum(1 for gap in gaps if gap > 1000),
                "over3000Ms": sum(1 for gap in gaps if gap > 3000),
                "anomalies": anomalies[:200],
            }
        qwen_count = stage_counts["qwen"]
        loss_rates = {
            stage: (round(max(0, qwen_count - count) / qwen_count, 6) if qwen_count else None)
            for stage, count in stage_counts.items()
        }
        return {
            "traceCount": len(records),
            "distributions": distributions,
            "revisionDiagnostics": {
                "stageCounts": stage_counts,
                "visibleStageCounts": visible_stage_counts,
                "lossRatesFromQwen": loss_rates,
                "revisionGaps": revision_gaps,
            },
        }

    def performance_traces(self, *, session_id: str, limit: int = 100) -> list[dict[str, object]]:
        with self._trace_lock:
            trace_ids = list(self._trace_order)[-max(1, min(4096, limit)):]
            return [
                dict(self._trace_records[trace_id])
                for trace_id in trace_ids
                if self._trace_records.get(trace_id, {}).get("sessionId") == session_id
            ]

    def record_delivery_metric(
        self,
        *,
        user_id: str,
        session_id: str,
        kind: str,
        duration_ms: int | None,
        attempt: int | None,
        reason: str | None,
    ) -> None:
        self.session_service.get_session(user_id=user_id, session_id=session_id)
        self._delivery_metric_counts[kind] += 1
        if duration_ms is not None:
            self._delivery_metric_latest_ms[kind] = duration_ms
        log_event(
            self.logger,
            logging.INFO,
            settings=self.settings,
            event="realtime_delivery.metric",
            session_id=session_id,
            kind=kind,
            duration_ms=duration_ms,
            attempt=attempt,
            reason=reason,
        )

    def register_desktop_device(self, *, device_id: str, manual_code: str, display_name: str, capabilities: dict[str, object]) -> DesktopDeviceRecord:
        code = manual_code.strip()
        if not code.isdigit() or len(code) != 6:
            raise DomainRequestError("realtime-speech", "register-device", "机器码必须是 6 位数字。", 400)
        now_ms = _now_ms()
        existing = self.repository.get_desktop_device_by_code(code)
        generation = (existing.generation + 1) if existing is not None and existing.device_id != device_id.strip() else (existing.generation if existing is not None else 1)
        stored = self.repository.save_desktop_device(DesktopDeviceRecord(
            device_id=device_id.strip(),
            manual_code=code,
            display_name=display_name.strip(),
            capabilities=dict(capabilities),
            registered_at_ms=now_ms,
            last_seen_at_ms=now_ms,
            status="online",
            generation=generation,
        ))
        self._log(logging.INFO, "realtime_speech.desktop_device_registered", session_id="desktop-registration", publisher_id=stored.device_id, state=stored.status)
        return stored

    def get_last_desktop_device_for_user(self, *, user_id: str) -> dict[str, object] | None:
        association = self.repository.get_last_account_desktop_device(user_id=user_id)
        if association is None:
            return None
        device = self.repository.get_desktop_device_by_code(association.manual_code)
        if device is None:
            return None
        online = self._desktop_device_fresh(device)
        return {
            "deviceId": device.device_id,
            "displayName": device.display_name,
            "maskedManualCode": f"••••{device.manual_code[-2:]}",
            "capabilities": device.capabilities,
            "online": online,
            "lastSeenAtMs": device.last_seen_at_ms,
            "accountBound": True,
            "devicePresence": "online" if online else "offline",
            "permissionStatus": self._permission_status(device),
        }

    def list_desktop_devices_for_user(self, *, user_id: str) -> list[dict[str, object]]:
        active_bindings = {
            item.device_id: item
            for item in self.repository.list_session_desktop_bindings_for_user(user_id=user_id)
            if item.status == "bound"
        }
        devices: list[dict[str, object]] = []
        for association in self.repository.list_account_desktop_devices(user_id=user_id):
            device = self.repository.get_desktop_device_by_code(association.manual_code)
            if device is None or device.device_id != association.device_id:
                continue
            online = self._desktop_device_fresh(device)
            binding = active_bindings.get(device.device_id)
            devices.append({
                "deviceId": device.device_id,
                "displayName": device.display_name,
                "maskedManualCode": f"••••{device.manual_code[-2:]}",
                "capabilities": dict(device.capabilities),
                "online": online,
                "lastSeenAtMs": device.last_seen_at_ms,
                "linkedAtMs": association.linked_at_ms,
                "lastUsedAtMs": association.last_used_at_ms,
                "accountBound": True,
                "devicePresence": "online" if online else "offline",
                "permissionStatus": self._permission_status(device),
                "activeInterview": None if binding is None else {
                    "sessionId": binding.session_id,
                    "bindingId": binding.binding_id,
                    "connectedAtMs": binding.bound_at_ms,
                },
            })
        return devices

    def bind_desktop_device(
        self,
        *,
        user_id: str,
        session_id: str,
        manual_code: str | None,
        reuse_last_device: bool = False,
    ) -> SessionDesktopBindingRecord:
        self.session_service.get_session(user_id=user_id, session_id=session_id)
        if self.get_active_interview_conflict(user_id=user_id, session_id=session_id) is not None:
            raise DomainRequestError(
                "realtime-speech",
                "bind-device",
                "当前账号已有一场进行中的面试，请先继续或结束上一场面试。",
                409,
                error_code="active_interview_conflict",
            )
        with self._frame_worker_lock:
            self._retired_session_ids.discard(session_id)
        if reuse_last_device:
            association = self.repository.get_last_account_desktop_device(user_id=user_id)
            if association is None:
                raise DomainRequestError("realtime-speech", "bind-device", "没有可复用的历史设备，请输入助手中的机器码。", 404)
            code = association.manual_code
        else:
            code = (manual_code or "").strip()
            if not code.isdigit() or len(code) != 6:
                raise DomainRequestError("realtime-speech", "bind-device", "请输入电脑伴随程序显示的 6 位机器码。", 400)
        device = self.repository.get_desktop_device_by_code(code)
        if device is None:
            raise DomainRequestError("realtime-speech", "bind-device", "未找到对应机器码。请确认电脑伴随程序已打开，并输入 6 位验证码。", 404)
        if not self._desktop_device_fresh(device):
            raise DomainRequestError("realtime-speech", "bind-device", "上次使用的设备当前离线，请打开助手或输入其他机器码。", 409)
        now_ms = _now_ms()
        previous_association = self.repository.get_account_desktop_device(user_id=user_id, device_id=device.device_id)
        self.repository.save_account_desktop_device(AccountDesktopDeviceRecord(
            owner_user_id=user_id,
            device_id=device.device_id,
            manual_code=device.manual_code,
            linked_at_ms=previous_association.linked_at_ms if previous_association else now_ms,
            last_used_at_ms=now_ms,
        ))
        current_binding = self.repository.get_session_desktop_binding(user_id=user_id, session_id=session_id)
        if current_binding is not None and current_binding.device_id == device.device_id and self._binding_is_active(binding=current_binding, device=device):
            return current_binding
        previous_bindings = {
            (item.owner_user_id, item.session_id): item
            for item in self.repository.list_session_desktop_bindings_for_user(user_id=user_id)
        }
        previous_bindings.update({
            (item.owner_user_id, item.session_id): item
            for item in self.repository.list_session_desktop_bindings_for_device(
            device_id=device.device_id,
            manual_code=device.manual_code,
            )
        })
        reset_current_session = False
        retired_session_ids: set[str] = set()
        for previous in previous_bindings.values():
            if previous.status != "bound":
                continue
            if previous.session_id != session_id:
                self.repository.save_session_desktop_binding(replace(previous, status="stale"))
                retired_session_ids.add(previous.session_id)
            else:
                reset_current_session = True
            for publisher in self.repository.list_publishers_for_session(session_id=previous.session_id):
                if publisher.status in {"closed", "failed"}:
                    continue
                self.repository.save_publisher(replace(
                    publisher,
                    disconnected_at_ms=now_ms,
                    status="closed",
                ))
        for retired_session_id in retired_session_ids:
            self._reset_realtime_session(session_id=retired_session_id, retired=True)
        if reset_current_session:
            self._reset_realtime_session(session_id=session_id, retired=False)
        binding = self.repository.save_session_desktop_binding(SessionDesktopBindingRecord(
            binding_id=f"desktop-binding-{uuid4().hex}",
            session_id=session_id,
            owner_user_id=user_id,
            device_id=device.device_id,
            manual_code=device.manual_code,
            display_name=device.display_name,
            capabilities=device.capabilities,
            bound_at_ms=now_ms,
            last_seen_at_ms=device.last_seen_at_ms,
            status="bound",
            binding_generation=device.generation,
        ))
        self._save_event(
            session_id=session_id,
            owner_user_id=user_id,
            kind="connection-state",
            payload={"deviceId": binding.device_id, "status": "bound", "displayName": binding.display_name},
        )
        self._log(logging.INFO, "realtime_speech.desktop_device_bound", session_id=session_id, publisher_id=binding.device_id, state=binding.status)
        return binding

    def get_active_interview_conflict(self, *, user_id: str, session_id: str) -> InterviewSessionRecord | None:
        self.session_service.get_session(user_id=user_id, session_id=session_id)
        self.reconcile_idle_sessions(user_id=user_id)
        conflicts = [
            session
            for session in self.session_service.list_sessions(user_id=user_id, status="live")
            if session.session_id != session_id
        ]
        if not conflicts:
            return None
        return max(conflicts, key=lambda session: (session.last_activity_at_ms, session.updated_at_ms))

    def supersede_active_interviews(
        self,
        *,
        user_id: str,
        session_id: str,
        expected_previous_session_id: str,
    ) -> list[str]:
        self.session_service.get_session(user_id=user_id, session_id=session_id)
        conflicts = [
            session
            for session in self.session_service.list_sessions(user_id=user_id, status="live")
            if session.session_id != session_id
        ]
        if not conflicts:
            return []
        conflict_ids = {session.session_id for session in conflicts}
        if expected_previous_session_id not in conflict_ids:
            raise DomainRequestError(
                "realtime-speech",
                "supersede-session",
                "进行中的面试已发生变化，请刷新后重新选择。",
                409,
                error_code="active_interview_changed",
            )
        now_ms = _now_ms()
        for conflict in conflicts:
            self.session_service.end_session(user_id=user_id, session_id=conflict.session_id)
            for binding in self.repository.list_session_desktop_bindings_for_user(user_id=user_id):
                if binding.session_id == conflict.session_id and binding.status == "bound":
                    self.repository.save_session_desktop_binding(replace(binding, status="stale"))
            for publisher in self.repository.list_publishers_for_session(session_id=conflict.session_id):
                if publisher.status not in {"closed", "failed"}:
                    self.repository.save_publisher(replace(publisher, disconnected_at_ms=now_ms, status="closed"))
            self._reset_realtime_session(session_id=conflict.session_id, retired=True)
            self._save_event(
                session_id=conflict.session_id,
                owner_user_id=user_id,
                kind="connection-state",
                payload={"status": "superseded", "replacementSessionId": session_id},
            )
        return sorted(conflict_ids)

    def terminate_session_for_admin(self, *, user_id: str, session_id: str) -> dict[str, object]:
        session = self.session_service.get_session(user_id=user_id, session_id=session_id)
        already_ended = session.status == "ended"
        if not already_ended:
            session = self.session_service.end_session(user_id=user_id, session_id=session_id)
        now_ms = _now_ms()
        released_bindings = 0
        closed_publishers = 0
        for binding in self.repository.list_session_desktop_bindings_for_user(user_id=user_id):
            if binding.session_id == session_id and binding.status == "bound":
                self.repository.save_session_desktop_binding(replace(binding, status="stale"))
                released_bindings += 1
        for publisher in self.repository.list_publishers_for_session(session_id=session_id):
            if publisher.status not in {"closed", "failed"}:
                self.repository.save_publisher(
                    replace(publisher, disconnected_at_ms=now_ms, status="closed")
                )
                closed_publishers += 1
        self._stop_realtime_metering(session_id=session_id)
        self._reset_realtime_session(session_id=session_id, retired=True)
        self._save_event(
            session_id=session_id,
            owner_user_id=user_id,
            kind="connection-state",
            payload={"status": "terminated-by-admin"},
        )
        return {
            "session_id": session_id,
            "status": session.status,
            "already_ended": already_ended,
            "released_bindings": released_bindings,
            "closed_publishers": closed_publishers,
        }

    def reconcile_idle_session(self, *, user_id: str, session_id: str) -> dict[str, object]:
        status = self.session_service.idle_status(user_id=user_id, session_id=session_id)
        if status["state"] != "expired":
            return status
        result = self.terminate_session_for_admin(user_id=user_id, session_id=session_id)
        return {**status, "state": "ended", "autoEnded": True, "release": result}

    def reconcile_idle_sessions(self, *, user_id: str | None = None) -> list[str]:
        expired = self.session_service.list_idle_live_sessions(user_id=user_id)
        ended: list[str] = []
        for session in expired:
            self.terminate_session_for_admin(user_id=session.owner_user_id, session_id=session.session_id)
            ended.append(session.session_id)
        return ended

    def record_web_session_heartbeat(self, *, user_id: str, session_id: str, binding_id: str | None, page: str, page_instance_id: str | None = None) -> WebSessionHeartbeatRecord:
        idle = self.reconcile_idle_session(user_id=user_id, session_id=session_id)
        session = self.session_service.get_session(user_id=user_id, session_id=session_id)
        if session.status == "ended":
            raise DomainRequestError(
                "realtime-speech",
                "web-heartbeat",
                "该面试已结束，实时页面连接已停止。",
                409,
                error_code="realtime_session_ended",
            )
        safe_page = "live" if page == "live" else "preparation"
        now_ms = _now_ms()
        heartbeat_record = WebSessionHeartbeatRecord(
            session_id=session_id,
            owner_user_id=user_id,
            page=safe_page,  # type: ignore[arg-type]
            binding_id=binding_id,
            seen_at_ms=now_ms,
            page_instance_id=page_instance_id.strip() if page_instance_id else None,
            lease_expires_at_ms=now_ms + self.settings.realtime_web_heartbeat_ttl_seconds * 1000,
        )
        if safe_page == "live" and heartbeat_record.page_instance_id:
            return self.repository.claim_live_web_session(heartbeat_record)
        active_live = self.repository.get_active_live_web_session(user_id=user_id)
        if (
            safe_page == "preparation"
            and active_live is not None
            and active_live.session_id == session_id
            and active_live.lease_expires_at_ms >= now_ms
        ):
            return active_live
        return self.repository.save_web_session_heartbeat(heartbeat_record)

    def require_active_realtime_session(self, *, user_id: str, session_id: str, page_instance_id: str | None = None, lease_generation: int | None = None) -> None:
        session = self.session_service.get_session(user_id=user_id, session_id=session_id)
        if session.status != "live":
            raise DomainRequestError(
                "realtime-speech",
                "stream-session",
                "当前面试已结束或已被新的面试接管。",
                410,
                "realtime_session_replaced",
            )
        active_page = self.repository.get_active_live_web_session(user_id=user_id)
        if active_page is None or active_page.lease_expires_at_ms < _now_ms():
            return
        # The lease selects the user's authoritative interview session, not one
        # browser window. Multiple authenticated pages may observe that same
        # session, while pages for a replaced session remain rejected.
        if active_page.session_id != session_id:
            raise DomainRequestError(
                "realtime-speech",
                "stream-page-lease",
                "当前实时页面所属面试已被其他面试接管。",
                409,
                "realtime_page_replaced",
            )

    def record_desktop_device_heartbeat(self, *, device_id: str, manual_code: str, display_name: str | None, capabilities: dict[str, object]) -> DesktopDeviceRecord:
        device = self.repository.get_desktop_device_by_code(manual_code.strip())
        if device is None or device.device_id != device_id.strip():
            return self.register_desktop_device(
                device_id=device_id,
                manual_code=manual_code,
                display_name=display_name or "面试稳伴随程序",
                capabilities=capabilities,
            )
        now_ms = _now_ms()
        return self.repository.save_desktop_device(replace(
            device,
            display_name=(display_name.strip() if display_name else device.display_name),
            capabilities={**device.capabilities, **dict(capabilities)},
            last_seen_at_ms=now_ms,
            status="online",
        ))

    def get_desktop_binding(self, *, user_id: str, session_id: str) -> SessionDesktopBindingRecord:
        self.session_service.get_session(user_id=user_id, session_id=session_id)
        binding = self.repository.get_session_desktop_binding(user_id=user_id, session_id=session_id)
        if binding is None:
            raise DomainRequestError("realtime-speech", "get-device-binding", "本场面试尚未绑定电脑伴随程序。", 404)
        return binding

    def get_desktop_active_binding(self, *, device_id: str, manual_code: str) -> SessionDesktopBindingRecord:
        code = manual_code.strip()
        requested_device_id = device_id.strip()
        device = self.repository.get_desktop_device_by_code(code)
        if device is None:
            raise DomainRequestError("realtime-speech", "desktop-active-binding", "这台电脑尚未登记或机器码不匹配。", 404)
        binding = self.repository.get_latest_session_desktop_binding_for_device(device_id=requested_device_id, manual_code=device.manual_code)
        if binding is None and device.device_id != requested_device_id:
            binding = self.repository.get_latest_session_desktop_binding_for_device(device_id=device.device_id, manual_code=device.manual_code)
        if binding is None:
            binding = self.repository.get_latest_session_desktop_binding_by_code(manual_code=device.manual_code)
        if binding is None:
            raise DomainRequestError("realtime-speech", "desktop-active-binding", "网页端尚未输入该机器码绑定面试。", 404)
        if not self._binding_is_active(binding=binding, device=device):
            raise DomainRequestError("realtime-speech", "desktop-active-binding", "网页端绑定已过期，请打开面试页面重新验证机器码。", 404)
        return binding

    def get_desktop_capture_binding(self, *, device_id: str, manual_code: str) -> SessionDesktopBindingRecord:
        code = manual_code.strip()
        requested_device_id = device_id.strip()
        device = self.repository.get_desktop_device_by_code(code)
        if device is None:
            raise DomainRequestError("realtime-speech", "desktop-capture-binding", "这台电脑尚未登记或机器码不匹配。", 404)
        binding = self.repository.get_latest_session_desktop_binding_for_device(device_id=requested_device_id, manual_code=device.manual_code)
        if binding is None and device.device_id != requested_device_id:
            binding = self.repository.get_latest_session_desktop_binding_for_device(device_id=device.device_id, manual_code=device.manual_code)
        if binding is None:
            binding = self.repository.get_latest_session_desktop_binding_by_code(manual_code=device.manual_code)
        if binding is None:
            raise DomainRequestError("realtime-speech", "desktop-capture-binding", "网页端尚未输入该机器码绑定面试。", 404)
        if binding.status != "bound":
            raise DomainRequestError("realtime-speech", "desktop-capture-binding", "网页端绑定已失效，请重新绑定机器码。", 404)
        if binding.binding_generation != device.generation:
            raise DomainRequestError("realtime-speech", "desktop-capture-binding", "伴随程序已重新登记，请在面试页重新绑定机器码。", 404)
        if not self._desktop_device_fresh(device):
            raise DomainRequestError("realtime-speech", "desktop-capture-binding", "电脑伴随程序心跳已过期，请保持伴随程序打开。", 404)
        try:
            session_status = self.session_service.get_session(user_id=binding.owner_user_id, session_id=binding.session_id).status
        except DomainRequestError:
            raise DomainRequestError("realtime-speech", "desktop-capture-binding", "当前面试不存在或已不可用。", 404)
        if session_status not in {"preparing", "live"}:
            raise DomainRequestError("realtime-speech", "desktop-capture-binding", "当前面试已结束，不能继续截图回答。", 409)
        return binding

    def get_desktop_active_binding_by_code(self, *, manual_code: str) -> SessionDesktopBindingRecord:
        code = manual_code.strip()
        device = self.repository.get_desktop_device_by_code(code)
        binding = self.repository.get_latest_session_desktop_binding_by_code(manual_code=code)
        if binding is None:
            if device is None:
                raise DomainRequestError("realtime-speech", "desktop-active-binding", "这台电脑尚未登记或机器码不匹配。", 404)
            raise DomainRequestError("realtime-speech", "desktop-active-binding", "网页端尚未输入该机器码绑定面试。", 404)
        if device is None or not self._binding_is_active(binding=binding, device=device):
            raise DomainRequestError("realtime-speech", "desktop-active-binding", "网页端绑定已过期，请打开面试页面重新验证机器码。", 404)
        return binding

    def get_desktop_pairing_status(self, *, manual_code: str, device_id: str | None = None) -> dict[str, object]:
        code = manual_code.strip()
        if not code.isdigit() or len(code) != 6:
            return {
                "state": "invalid-code",
                "manualCode": code,
                "requestedDeviceId": device_id,
                "registered": False,
                "bound": False,
                "message": "机器码必须是 6 位数字。",
            }
        device = self.repository.get_desktop_device_by_code(code)
        device_presence = "online" if device is not None and self._desktop_device_fresh(device) else "offline"
        permission_status = self._permission_status(device)
        binding = self.repository.get_latest_session_desktop_binding_by_code(manual_code=code)
        if binding is not None:
            session_status = "unknown"
            try:
                session_status = self.session_service.get_session(user_id=binding.owner_user_id, session_id=binding.session_id).status
            except DomainRequestError:
                session_status = "missing"
            active = device is not None and self._binding_is_active(binding=binding, device=device)
            if not active:
                stale_reason = self._binding_stale_reason(binding=binding, device=device)
                return {
                    "state": "stale-bound",
                    "manualCode": code,
                    "requestedDeviceId": device_id,
                    "registered": device is not None and self._desktop_device_fresh(device),
                    "registeredDeviceId": device.device_id if device else binding.device_id,
                    "bound": False,
                    "devicePresence": device_presence,
                    "permissionStatus": permission_status,
                    "sessionConnection": "disconnected",
                    "sessionStatus": session_status,
                    "staleReason": stale_reason,
                    "message": self._stale_binding_message(stale_reason),
                    "binding": self.desktop_binding_response(replace(binding, status="stale")).model_dump(by_alias=True),
                }
            return {
                "state": "bound",
                "manualCode": code,
                "requestedDeviceId": device_id,
                "registered": device is not None,
                "registeredDeviceId": device.device_id if device else binding.device_id,
                "bound": True,
                "devicePresence": device_presence,
                "permissionStatus": permission_status,
                "sessionConnection": "connected",
                "sessionStatus": session_status,
                "captureState": self.capture_control_state(session_id=binding.session_id) if session_status == "live" else "ready",
                "message": "网页端已绑定本机。",
                "binding": self.desktop_binding_response(binding).model_dump(by_alias=True),
            }
        if device is not None:
            return {
                "state": "registered",
                "manualCode": code,
                "requestedDeviceId": device_id,
                "registered": True,
                "registeredDeviceId": device.device_id,
                "bound": False,
                "devicePresence": device_presence,
                "permissionStatus": permission_status,
                "sessionConnection": "idle",
                "message": "这台电脑已登记，网页端尚未绑定该机器码。",
            }
        return {
            "state": "not-registered",
            "manualCode": code,
            "requestedDeviceId": device_id,
            "registered": False,
            "bound": False,
            "devicePresence": "offline",
            "permissionStatus": {},
            "sessionConnection": "disconnected",
            "message": "后端尚未登记这台电脑，请保持伴随程序打开。",
        }

    def capture_control_state(self, *, session_id: str) -> str:
        cached = self._capture_control_cache.get(session_id)
        if cached is not None:
            return cached
        latest = next(
            (
                event for event in reversed(self.repository.list_events_for_session(session_id=session_id))
                if event.kind == "capture-control"
            ),
            None,
        )
        state = latest.payload.get("captureState") if latest is not None else None
        resolved = "paused" if state == "paused" else "capturing"
        self._capture_control_cache[session_id] = resolved
        return resolved

    def control_capture(self, *, user_id: str, session_id: str, action: str) -> dict[str, object]:
        session = self.session_service.get_session(user_id=user_id, session_id=session_id)
        if session.status != "live":
            raise DomainRequestError("realtime-speech", "capture-control", "只有进行中的面试可以暂停或恢复收音。", 409, "session_not_live")
        if action not in {"pause", "resume"}:
            raise DomainRequestError("realtime-speech", "capture-control", "不支持的收音控制操作。", 400, "capture_control_invalid")
        if action == "resume" and not self._settle_realtime_minute(user_id=user_id, session_id=session_id):
            raise DomainRequestError(
                "billing",
                "realtime-minute",
                "积分不足，实时面试每分钟需要 5 点，请充值或购买会员后恢复收音。",
                402,
                error_code="realtime_minute_insufficient_balance",
            )
        capture_state = "paused" if action == "pause" else "capturing"
        if self.capture_control_state(session_id=session_id) != capture_state:
            self._save_event(
                session_id=session_id,
                owner_user_id=user_id,
                kind="capture-control",
                payload={"action": action, "captureState": capture_state},
            )
        self._capture_control_cache[session_id] = capture_state
        if action == "pause":
            self._stop_realtime_metering(session_id=session_id)
            self.asr_gateway.close_session(session_id=session_id)
        else:
            self._ensure_realtime_metering(user_id=user_id, session_id=session_id)
            self._prewarm_asr_session(session_id=session_id)
        self.session_service.touch_activity(user_id=user_id, session_id=session_id, force=True)
        return {"sessionId": session_id, "captureState": capture_state}

    def get_desktop_active_connection(self, *, device_id: str, manual_code: str) -> dict[str, object]:
        status = self.get_desktop_pairing_status(manual_code=manual_code, device_id=device_id)
        binding = status.get("binding")
        lease_version = None
        if status.get("bound") is True and isinstance(binding, dict):
            lease_version = f"{binding.get('bindingId', '')}:{binding.get('bindingGeneration', 1)}"
        return {
            **status,
            "authoritative": True,
            "leaseVersion": lease_version,
            "refreshAfterMs": 1_000,
        }

    def _desktop_device_fresh(self, device: DesktopDeviceRecord) -> bool:
        return (_now_ms() - device.last_seen_at_ms) <= self.settings.realtime_desktop_heartbeat_ttl_seconds * 1000

    @staticmethod
    def _permission_status(device: DesktopDeviceRecord | None) -> dict[str, object]:
        if device is None:
            return {}
        capabilities = device.capabilities
        return {
            "microphone": capabilities.get("microphone", "unknown"),
            "systemAudio": capabilities.get("systemAudio", "unknown"),
            "screenCapture": capabilities.get("screenCapture", "unknown"),
        }

    def _web_heartbeat_fresh(self, *, user_id: str, session_id: str) -> bool:
        heartbeat = self.repository.get_web_session_heartbeat(user_id=user_id, session_id=session_id)
        if heartbeat is None:
            return False
        return (_now_ms() - heartbeat.seen_at_ms) <= self.settings.realtime_web_heartbeat_ttl_seconds * 1000

    def _binding_is_active(self, *, binding: SessionDesktopBindingRecord, device: DesktopDeviceRecord | None) -> bool:
        if device is None:
            return False
        if binding.status != "bound":
            return False
        if binding.binding_generation != device.generation:
            return False
        if not self._desktop_device_fresh(device):
            return False
        try:
            session_status = self.session_service.get_session(user_id=binding.owner_user_id, session_id=binding.session_id).status
        except DomainRequestError:
            return False
        return session_status in {"preparing", "live"}

    def _binding_stale_reason(self, *, binding: SessionDesktopBindingRecord, device: DesktopDeviceRecord | None) -> str:
        if device is None:
            return "desktop-not-registered"
        if binding.binding_generation != device.generation:
            return "desktop-generation-changed"
        if not self._desktop_device_fresh(device):
            return "desktop-heartbeat-stale"
        try:
            session_status = self.session_service.get_session(user_id=binding.owner_user_id, session_id=binding.session_id).status
        except DomainRequestError:
            return "session-missing"
        if session_status not in {"preparing", "live"}:
            return "session-not-active"
        return "unknown"

    def _require_active_desktop_binding(
        self,
        *,
        publisher: RealtimePublisherRecord,
        device_id: str,
    ) -> SessionDesktopBindingRecord:
        binding = self.repository.get_session_desktop_binding(user_id=publisher.owner_user_id, session_id=publisher.session_id)
        if binding is None:
            raise DomainRequestError(
                "realtime-speech",
                "audio-frame",
                "未检测到本会话的桌面端绑定，请先在网页端输入机器码并完成桌面绑定。",
                409,
                "machine_code_not_bound",
            )
        if binding.device_id != device_id:
            raise DomainRequestError(
                "realtime-speech",
                "audio-frame",
                "桌面采集端设备与会话绑定设备不一致，请检查当前机器码并重新绑定。",
                409,
                "desktop_device_mismatch",
            )
        device = self.repository.get_desktop_device_by_code(binding.manual_code)
        stale_reason = self._binding_stale_reason(binding=binding, device=device)
        if stale_reason != "unknown":
            raise DomainRequestError(
                "realtime-speech",
                "audio-frame",
                self._stale_binding_message(stale_reason),
                409,
                stale_reason,
            )
        return binding

    @staticmethod
    def _stale_binding_message(reason: str) -> str:
        return {
            "desktop-not-registered": "后端没有这台电脑的在线登记，请保持伴随程序打开。",
            "desktop-generation-changed": "该机器码已被新的电脑登记，历史绑定已失效。",
            "desktop-heartbeat-stale": "电脑伴随程序心跳已过期，请重新打开伴随程序。",
            "web-heartbeat-missing": "网页端没有活跃心跳，请打开面试准备页或面试页重新绑定。",
            "session-missing": "历史绑定的面试不存在。",
            "session-not-active": "历史绑定的面试已结束或不可用。",
        }.get(reason, "历史绑定已失效，请重新验证机器码。")

    def create_publisher(self, *, user_id: str, session_id: str, source_kind: RealtimeSourceKind, client_name: str) -> RealtimePublisherRecord:
        session = self.session_service.get_session(user_id=user_id, session_id=session_id)
        if session.status != "live":
            raise DomainRequestError("realtime-speech", "create-publisher", "只有进行中的面试会话才能创建实时语音发布者。", 400)
        if self.capture_control_state(session_id=session_id) == "paused":
            raise DomainRequestError("realtime-speech", "create-publisher", "当前面试已暂停收音，请先在网页端恢复收音。", 409, "capture_paused")
        self._ensure_realtime_metering(user_id=user_id, session_id=session_id)
        now_ms = _now_ms()
        safe_client_name = client_name.strip()
        for previous in self.repository.list_publishers_for_session(session_id=session_id):
            if (
                previous.owner_user_id == user_id
                and previous.source_kind == source_kind
                and previous.status not in {"closed", "failed"}
            ):
                self.repository.save_publisher(replace(previous, disconnected_at_ms=now_ms, status="closed"))
        publisher = RealtimePublisherRecord(
            publisher_id=f"publisher-{uuid4().hex}",
            token=f"rt-{uuid4().hex}",
            session_id=session_id,
            owner_user_id=user_id,
            source_kind=source_kind,
            client_name=safe_client_name,
            issued_at_ms=now_ms,
            expires_at_ms=now_ms + self.settings.realtime_publisher_ttl_seconds * 1000,
            status="connected",
        )
        stored = self.repository.save_publisher(publisher)
        active_publisher_ids = {
            item.publisher_id
            for item in self.repository.list_publishers_for_session(session_id=session_id)
            if item.owner_user_id == user_id and item.status not in {"closed", "failed"}
        }
        self.repository.prune_publishers_for_session(
            session_id=session_id,
            keep_publisher_ids=active_publisher_ids | {stored.publisher_id},
        )
        self._save_event(
            session_id=session_id,
            owner_user_id=user_id,
            kind="connection-state",
            payload={"publisherId": stored.publisher_id, "status": stored.status, "sourceKind": stored.source_kind},
        )
        return stored

    def connect_publisher(self, *, token: str) -> RealtimePublisherRecord:
        publisher = self._require_publisher_token(token)
        if _now_ms() > publisher.expires_at_ms:
            raise DomainRequestError("realtime-speech", "connect", "实时语音发布令牌已过期。", 410)
        connected = self.repository.save_publisher(replace(publisher, connected_at_ms=_now_ms(), status="connected"))
        self._publisher_status_cache[connected.publisher_id] = connected.status
        self._save_event(
            session_id=connected.session_id,
            owner_user_id=connected.owner_user_id,
            kind="connection-state",
            payload={"publisherId": connected.publisher_id, "status": connected.status, "sourceKind": connected.source_kind},
        )
        self._log(logging.INFO, "realtime_speech.publisher_connected", session_id=connected.session_id, publisher_id=connected.publisher_id, state=connected.status)
        return connected

    def disconnect_publisher(self, *, token: str, final_state: str = "closed") -> RealtimePublisherRecord:
        publisher = self.repository.get_publisher_by_token(token)
        if publisher is None:
            raise DomainRequestError("realtime-speech", "publisher-token", "实时语音发布令牌无效。", 404)
        if publisher.status in {"closed", "failed"}:
            return publisher
        updated = self.repository.save_publisher(replace(publisher, disconnected_at_ms=_now_ms(), status=final_state))  # type: ignore[arg-type]
        self._publisher_status_cache.pop(updated.publisher_id, None)
        self._save_event(
            session_id=updated.session_id,
            owner_user_id=updated.owner_user_id,
            kind="connection-state",
            payload={"publisherId": updated.publisher_id, "status": updated.status, "sourceKind": updated.source_kind},
        )
        return updated

    def process_audio_frame(
        self,
        *,
        token: str,
        device_id: str,
        source_id: str,
        sequence: int,
        source_kind: RealtimeSourceKind,
        segment_id: str,
        revision: int,
        captured_at_ms: int,
        started_at_ms: int,
        vad_triggered_at_ms: int | None = None,
        speech_confirmed_at_ms: int | None = None,
        ended_at_ms: int,
        duration_ms: int,
        codec: str,
        sample_rate_hz: int,
        channels: int,
        is_final: bool,
        trace_id: str | None,
        sent_at_ms: int | None,
        audio_base64: str,
        diagnostics: dict[str, object] | None = None,
        turn_state: str | None = None,
        finalization_reason: str | None = None,
        source_generation: int | None = None,
        terminal_id: str | None = None,
    ) -> list[dict[str, object]]:
        prepared = self._prepare_audio_frame(
            token=token,
            device_id=device_id,
            source_id=source_id,
            sequence=sequence,
            source_kind=source_kind,
            segment_id=segment_id,
            revision=revision,
            captured_at_ms=captured_at_ms,
            started_at_ms=started_at_ms,
            vad_triggered_at_ms=vad_triggered_at_ms,
            speech_confirmed_at_ms=speech_confirmed_at_ms,
            ended_at_ms=ended_at_ms,
            duration_ms=duration_ms,
            codec=codec,
            sample_rate_hz=sample_rate_hz,
            channels=channels,
            is_final=is_final,
            turn_state=turn_state,
            finalization_reason=finalization_reason,
            source_generation=source_generation,
            terminal_id=terminal_id,
            trace_id=trace_id,
            sent_at_ms=sent_at_ms,
            diagnostics=diagnostics,
            audio_base64=audio_base64,
        )
        publisher = prepared.get("publisher")
        if isinstance(publisher, RealtimePublisherRecord):
            self.session_service.touch_activity(user_id=publisher.owner_user_id, session_id=publisher.session_id)
        return self._process_prepared_audio_frame(prepared)

    def enqueue_audio_frame(
        self,
        *,
        token: str,
        device_id: str,
        source_id: str,
        sequence: int,
        source_kind: RealtimeSourceKind,
        segment_id: str,
        revision: int,
        captured_at_ms: int,
        started_at_ms: int,
        vad_triggered_at_ms: int | None = None,
        speech_confirmed_at_ms: int | None = None,
        ended_at_ms: int,
        duration_ms: int,
        codec: str,
        sample_rate_hz: int,
        channels: int,
        is_final: bool,
        trace_id: str | None,
        sent_at_ms: int | None,
        diagnostics: dict[str, object] | None = None,
        audio_base64: str = "",
        audio_bytes: bytes | None = None,
        turn_state: str | None = None,
        finalization_reason: str | None = None,
        source_generation: int | None = None,
        terminal_id: str | None = None,
        authenticated_publisher: RealtimePublisherRecord | None = None,
    ) -> list[dict[str, object]]:
        prepared = self._prepare_audio_frame(
            token=token,
            device_id=device_id,
            source_id=source_id,
            sequence=sequence,
            source_kind=source_kind,
            segment_id=segment_id,
            revision=revision,
            captured_at_ms=captured_at_ms,
            started_at_ms=started_at_ms,
            vad_triggered_at_ms=vad_triggered_at_ms,
            speech_confirmed_at_ms=speech_confirmed_at_ms,
            ended_at_ms=ended_at_ms,
            duration_ms=duration_ms,
            codec=codec,
            sample_rate_hz=sample_rate_hz,
            channels=channels,
            is_final=is_final,
            turn_state=turn_state,
            finalization_reason=finalization_reason,
            source_generation=source_generation,
            terminal_id=terminal_id,
            trace_id=trace_id,
            sent_at_ms=sent_at_ms,
            diagnostics=diagnostics,
            audio_base64=audio_base64,
            audio_bytes=audio_bytes,
            authenticated_publisher=authenticated_publisher,
        )
        publisher = prepared.get("publisher")
        if not isinstance(publisher, RealtimePublisherRecord):
            return self._process_prepared_audio_frame(prepared)
        key = self._session_source_key(prepared["publisher"].session_id, prepared["frame"].source_kind)  # type: ignore[index]
        with self._frame_worker_lock:
            work_queue = self._frame_queues.get(key)
            worker = self._frame_workers.get(key)
            if work_queue is None:
                work_queue = queue.Queue(maxsize=max(8, self.settings.realtime_ingress_queue_max_frames))
                self._frame_queues[key] = work_queue
            if worker is None or not worker.is_alive():
                worker = threading.Thread(target=self._frame_worker_loop, args=(key, work_queue), daemon=True)
                worker.start()
                self._frame_workers[key] = worker
            counter_bucket = prepared.get("counter_bucket")
            if isinstance(counter_bucket, dict):
                counter_bucket["queueDepth"] = max(counter_bucket.get("queueDepth", 0), work_queue.qsize() + 1)
        frame = prepared.get("frame")
        assert isinstance(frame, AudioFrame)
        prepared["queue_enter_at_ms"] = _now_ms()
        self._observe_trace(frame.trace_id, queueEnterAtMs=prepared["queue_enter_at_ms"])
        self._track_source_turn(prepared)
        try:
            work_queue.put_nowait(prepared)
        except queue.Full:
            counter_bucket = prepared.get("counter_bucket")
            if isinstance(counter_bucket, dict):
                counter_bucket["droppedPartialUpdates"] = int(counter_bucket.get("droppedPartialUpdates", 0)) + 1
            if not frame.is_final:
                return [{"kind": "degraded", "payload": {
                    "reason": "partial-coalesced-under-pressure",
                    "sourceKind": frame.source_kind,
                    "sequence": frame.sequence,
                }}]
            displaced = self._replace_queued_partial_with_terminal(work_queue, prepared)
            if displaced:
                if frame.terminal_id:
                    self._mark_terminal_accepted(frame)
                if isinstance(counter_bucket, dict):
                    counter_bucket["terminalAdmissions"] = int(counter_bucket.get("terminalAdmissions", 0)) + 1
                return [self._terminal_ack(frame)] if frame.terminal_id else []
            try:
                work_queue.put(prepared, timeout=max(0.01, self.settings.realtime_terminal_admission_timeout_seconds))
            except queue.Full:
                if isinstance(counter_bucket, dict):
                    counter_bucket["terminalAdmissionFailures"] = int(counter_bucket.get("terminalAdmissionFailures", 0)) + 1
                return [{"kind": "degraded", "payload": {
                    "reason": "terminal-admission-timeout",
                    "sourceKind": frame.source_kind,
                    "segmentId": frame.segment_id,
                    "revision": frame.revision,
                    "terminalId": frame.terminal_id,
                    "displacedPartial": displaced is not None,
                }}]
        if frame.is_final and frame.terminal_id:
            self._mark_terminal_accepted(frame)
            if isinstance(counter_bucket, dict):
                counter_bucket["terminalAdmissions"] = int(counter_bucket.get("terminalAdmissions", 0)) + 1
            return [self._terminal_ack(frame)]
        return []

    def _track_source_turn(self, prepared: dict[str, object]) -> None:
        if not self.settings.realtime_source_watchdog_enabled:
            return
        frame = prepared.get("frame")
        publisher = prepared.get("publisher")
        if not isinstance(frame, AudioFrame) or not isinstance(publisher, RealtimePublisherRecord):
            return
        key = self._session_source_key(frame.session_id, frame.source_kind)
        with self._watchdog_lock:
            if frame.is_final:
                self._active_source_turns.pop(key, None)
            else:
                self._active_source_turns[key] = {
                    "publisher": publisher,
                    "frame": frame,
                    "lastFrameAtMs": _now_ms(),
                }
            if self._watchdog_thread is None or not self._watchdog_thread.is_alive():
                self._watchdog_thread = threading.Thread(
                    target=self._source_watchdog_loop,
                    name="realtime-source-watchdog",
                    daemon=True,
                )
                self._watchdog_thread.start()

    def _source_watchdog_loop(self) -> None:
        poll_seconds = max(0.1, self.settings.realtime_source_watchdog_poll_seconds)
        deadline_ms = max(1_000, int(self.settings.realtime_source_watchdog_seconds * 1_000))
        while self.settings.realtime_source_watchdog_enabled:
            sleep(poll_seconds)
            now_ms = _now_ms()
            expired: list[tuple[tuple[str, RealtimeSourceKind], dict[str, object]]] = []
            with self._watchdog_lock:
                for key, active in list(self._active_source_turns.items()):
                    if now_ms - int(active.get("lastFrameAtMs", now_ms)) < deadline_ms:
                        continue
                    expired.append((key, self._active_source_turns.pop(key)))
            for key, active in expired:
                self._finalize_abandoned_source_turn(key=key, active=active, now_ms=now_ms)
            with self._watchdog_lock:
                if not self._active_source_turns:
                    self._watchdog_thread = None
                    return

    def _finalize_abandoned_source_turn(
        self,
        *,
        key: tuple[str, RealtimeSourceKind],
        active: dict[str, object],
        now_ms: int,
    ) -> None:
        publisher = active.get("publisher")
        frame = active.get("frame")
        if not isinstance(publisher, RealtimePublisherRecord) or not isinstance(frame, AudioFrame):
            return
        # The watchdog removes an expired snapshot before performing provider
        # recovery. A fresh frame can arrive in that small gap and establish a
        # newer active turn for the same source. Never let the stale watchdog
        # snapshot close that fresh source connection.
        with self._watchdog_lock:
            replacement_active = self._active_source_turns.get(key)
            replacement_frame = replacement_active.get("frame") if replacement_active is not None else None
            replacement_at_ms = int(replacement_active.get("lastFrameAtMs", 0)) if replacement_active is not None else 0
        if isinstance(replacement_frame, AudioFrame) and (
            replacement_at_ms > int(active.get("lastFrameAtMs", 0))
            or replacement_frame.segment_id != frame.segment_id
            or replacement_frame.revision > frame.revision
        ):
            return
        self._close_asr_source(session_id=frame.session_id, source_kind=frame.source_kind)
        current = self.repository.get_transcript(frame.session_id, frame.segment_id)
        terminal_revision = max(frame.revision + 1, current.revision + 1 if current is not None else 1)
        if current is not None and not current.is_final:
            current = self.repository.save_transcript(replace(
                current,
                revision=terminal_revision,
                ended_at_ms=max(current.ended_at_ms, frame.ended_at_ms),
                is_final=True,
                terminal_state="incomplete",
                finalization_reason="backend-watchdog",
                published_at_ms=now_ms,
                usage=None,
            ))
        self.repository.save_publisher(replace(publisher, status="receiving-audio"))
        self._counter_bucket(session_id=key[0], source_kind=key[1])["incompleteRecoveries"] += 1
        self._save_event(
            session_id=publisher.session_id,
            owner_user_id=publisher.owner_user_id,
            kind="transcript-updated",
            payload={
                "segmentId": frame.segment_id,
                "revision": terminal_revision,
                "role": current.role if current is not None else ("candidate" if frame.source_kind == "microphone" else "interviewer"),
                "text": current.text if current is not None else "",
                "isFinal": True,
                "terminalState": "incomplete",
                "finalizationReason": "backend-watchdog",
                "publishedAtMs": now_ms,
            },
        )

    @staticmethod
    def _replace_queued_partial_with_terminal(
        work_queue: "queue.Queue[dict[str, object]]",
        terminal_job: dict[str, object],
    ) -> bool:
        """Atomically reserve a saturated queue slot without ever evicting a terminal."""
        terminal_frame = terminal_job.get("frame")
        if not isinstance(terminal_frame, AudioFrame) or not terminal_frame.is_final:
            return False
        # queue.Queue has no public replace operation. Its mutex is the same lock
        # used by put/get, so replacing one queued partial keeps task accounting
        # unchanged and cannot race another producer or the worker.
        with work_queue.mutex:
            for index, candidate in enumerate(work_queue.queue):
                candidate_frame = candidate.get("frame")
                if not isinstance(candidate_frame, AudioFrame) or candidate_frame.is_final:
                    continue
                replacement = terminal_job
                if candidate_frame.segment_id == terminal_frame.segment_id:
                    replacement = dict(terminal_job)
                    replacement["frame"] = replace(
                        terminal_frame,
                        started_at_ms=min(candidate_frame.started_at_ms, terminal_frame.started_at_ms),
                        duration_ms=max(
                            20,
                            terminal_frame.ended_at_ms - min(candidate_frame.started_at_ms, terminal_frame.started_at_ms),
                        ),
                        audio_bytes=candidate_frame.audio_bytes + terminal_frame.audio_bytes,
                    )
                work_queue.queue[index] = replacement
                work_queue.not_empty.notify()
                return True
        return False

    def _frame_worker_loop(self, key: tuple[str, RealtimeSourceKind], work_queue: "queue.Queue[dict[str, object]]") -> None:
        while True:
            try:
                job = work_queue.get(timeout=15)
            except queue.Empty:
                with self._frame_worker_lock:
                    if work_queue.empty():
                        self._frame_workers.pop(key, None)
                        self._frame_queues.pop(key, None)
                        return
                    continue
            jobs = [job]
            for _ in range(max(0, self.settings.realtime_ingress_coalesce_max_frames - 1)):
                try:
                    jobs.append(work_queue.get_nowait())
                except queue.Empty:
                    break
            try:
                for prepared in self._coalesce_prepared_frame_jobs(jobs):
                    with self._frame_worker_lock:
                        if key[0] in self._retired_session_ids:
                            continue
                    try:
                        self._process_prepared_audio_frame(prepared)
                    except DomainRequestError:
                        pass
            finally:
                for _ in jobs:
                    work_queue.task_done()
                self._counter_bucket(session_id=key[0], source_kind=key[1])["queueDepth"] = work_queue.qsize()

    @staticmethod
    def _coalesce_prepared_frame_jobs(jobs: list[dict[str, object]]) -> list[dict[str, object]]:
        """Combine adjacent incremental PCM frames without dropping their audio."""
        coalesced: list[dict[str, object]] = []
        for job in jobs:
            frame = job.get("frame")
            if not isinstance(frame, AudioFrame) or not coalesced:
                coalesced.append(job)
                continue
            previous = coalesced[-1]
            previous_frame = previous.get("frame")
            can_merge = (
                isinstance(previous_frame, AudioFrame)
                and not previous_frame.is_final
                and previous_frame.segment_id == frame.segment_id
                and previous_frame.source_kind == frame.source_kind
                and previous_frame.codec == frame.codec
                and previous_frame.sample_rate_hz == frame.sample_rate_hz
                and previous_frame.channels == frame.channels
            )
            if not can_merge:
                coalesced.append(job)
                continue
            merged = dict(job)
            merged["frame"] = replace(
                frame,
                started_at_ms=min(previous_frame.started_at_ms, frame.started_at_ms),
                duration_ms=max(20, frame.ended_at_ms - min(previous_frame.started_at_ms, frame.started_at_ms)),
                audio_bytes=previous_frame.audio_bytes + frame.audio_bytes,
            )
            merged["coalesced_frame_count"] = int(previous.get("coalesced_frame_count", 1)) + 1
            coalesced[-1] = merged
        return coalesced

    def _prepare_audio_frame(
        self,
        *,
        token: str,
        device_id: str,
        source_id: str,
        sequence: int,
        source_kind: RealtimeSourceKind,
        segment_id: str,
        revision: int,
        captured_at_ms: int,
        started_at_ms: int,
        vad_triggered_at_ms: int | None = None,
        speech_confirmed_at_ms: int | None = None,
        ended_at_ms: int,
        duration_ms: int,
        codec: str,
        sample_rate_hz: int,
        channels: int,
        is_final: bool,
        turn_state: str | None,
        finalization_reason: str | None,
        source_generation: int | None,
        terminal_id: str | None,
        trace_id: str | None,
        sent_at_ms: int | None,
        diagnostics: dict[str, object] | None = None,
        audio_base64: str = "",
        audio_bytes: bytes | None = None,
        authenticated_publisher: RealtimePublisherRecord | None = None,
    ) -> dict[str, object]:
        publisher = authenticated_publisher or self._require_publisher_token(token)
        if authenticated_publisher is None:
            session = self.session_service.get_session(user_id=publisher.owner_user_id, session_id=publisher.session_id)
            if session.status != "live":
                return {"early_events": []}
        if self.capture_control_state(session_id=publisher.session_id) == "paused":
            return {"early_events": []}
        ingest_received_at_ms = _now_ms()
        if source_kind == "mixed":
            degraded = self.repository.save_publisher(replace(publisher, status="degraded"))
            event = self._save_event(
                session_id=degraded.session_id,
                owner_user_id=degraded.owner_user_id,
                kind="degraded",
                payload={"publisherId": degraded.publisher_id, "reason": "mixed-input", "sourceKind": source_kind},
            )
            self._log(logging.WARNING, "realtime_speech.degraded", session_id=degraded.session_id, publisher_id=degraded.publisher_id, state="degraded", error_code="mixed_input")
            return {"early_events": [self._event_payload(event)]}
        source_key = self._session_source_key(publisher.session_id, source_kind)
        if source_generation is not None:
            with self._terminal_lock:
                latest_generation = self._latest_source_generations.get(source_key, 0)
                if source_generation < latest_generation:
                    return {"early_events": [{"kind": "degraded", "payload": {
                        "reason": "stale-source-generation",
                        "sourceKind": source_kind,
                        "sourceGeneration": source_generation,
                        "latestSourceGeneration": latest_generation,
                    }}]}
                self._latest_source_generations[source_key] = max(latest_generation, source_generation)
        if is_final and terminal_id:
            with self._terminal_lock:
                accepted = self._accepted_terminal_ids.get(source_key, {})
                accepted_at_ms = accepted.get(terminal_id)
            if accepted_at_ms is not None:
                duplicate_bucket = self._counter_bucket(session_id=publisher.session_id, source_kind=source_kind)
                duplicate_bucket["terminalDuplicates"] += 1
                duplicate_bucket["terminalResends"] += 1
                return {"early_events": [{"kind": "terminal-accepted", "payload": {
                    "sourceKind": source_kind,
                    "sourceId": source_id,
                    "sequence": sequence,
                    "segmentId": segment_id,
                    "revision": revision,
                    "terminalId": terminal_id,
                    "sourceGeneration": source_generation,
                    "acceptedAtMs": accepted_at_ms,
                    "duplicate": True,
                }}]}
        decoded_audio = audio_bytes if audio_bytes is not None else base64.b64decode(audio_base64.encode("utf-8"))
        frame = AudioFrame(
            publisher_id=publisher.publisher_id,
            session_id=publisher.session_id,
            device_id=device_id,
            source_id=source_id,
            source_kind=source_kind,
            segment_id=segment_id,
            revision=revision,
            sequence=sequence,
            captured_at_ms=captured_at_ms,
            started_at_ms=started_at_ms,
            ended_at_ms=ended_at_ms,
            duration_ms=duration_ms,
            codec=codec,  # type: ignore[arg-type]
            sample_rate_hz=sample_rate_hz,
            channels=channels,
            is_final=is_final,
            turn_state=turn_state,
            finalization_reason=finalization_reason,
            source_generation=source_generation,
            terminal_id=terminal_id,
            trace_id=trace_id,
            sent_at_ms=sent_at_ms,
            vad_triggered_at_ms=vad_triggered_at_ms,
            speech_confirmed_at_ms=speech_confirmed_at_ms,
            backend_received_at_ms=ingest_received_at_ms,
            diagnostics=dict(diagnostics or {}),
            audio_bytes=decoded_audio,
        )
        self._observe_trace(
            trace_id,
            sessionId=publisher.session_id,
            channel=source_kind,
            sequence=sequence,
            revision=revision,
            utteranceId=segment_id,
            desktopAudioCaptureAtMs=captured_at_ms,
            desktopWsSendAtMs=sent_at_ms,
            backendWsReceiveAtMs=ingest_received_at_ms,
            **{
                key: value
                for key, value in frame.diagnostics.items()
                if value is None or isinstance(value, (str, int, float, bool))
            },
        )
        if not frame.audio_bytes:
            degraded = self._save_event(
                session_id=publisher.session_id,
                owner_user_id=publisher.owner_user_id,
                kind="degraded",
                payload={
                    "publisherId": publisher.publisher_id,
                    "reason": "empty-audio-frame",
                    "sourceKind": source_kind,
                    "message": "该音频帧为空，已跳过本次转写。",
                },
            )
            return {"early_events": [self._event_payload(degraded)]}
        counter_bucket = self._counter_bucket(session_id=publisher.session_id, source_kind=source_kind)
        counter_bucket["chunksProduced"] += 1
        counter_bucket["chunksUploaded"] += 1
        counter_bucket["serializedAudioBytes"] += len(decoded_audio)
        previous = self.repository.get_frame_receipt(
            session_id=publisher.session_id,
            source_kind=source_kind,
            source_id=source_id,
        )
        pending_receipt = self.repository.save_frame_receipt(RealtimeFrameReceiptRecord(
            session_id=publisher.session_id,
            owner_user_id=publisher.owner_user_id,
            publisher_id=publisher.publisher_id,
            device_id=device_id,
            source_id=source_id,
            source_kind=source_kind,
            sequence=sequence,
            frame_count=(previous.frame_count + 1 if previous is not None else 1),
            captured_at_ms=captured_at_ms,
            received_at_ms=_now_ms(),
            asr_status="pending",
        ))
        return {
            "publisher": publisher,
            "frame": frame,
            "pending_receipt": pending_receipt,
            "counter_bucket": counter_bucket,
            "ingest_received_at_ms": ingest_received_at_ms,
            "captured_at_ms": captured_at_ms,
            "sent_at_ms": sent_at_ms,
            "source_kind": source_kind,
        }

    @staticmethod
    def _terminal_ack(frame: AudioFrame) -> dict[str, object]:
        return {"kind": "terminal-accepted", "payload": {
            "sourceKind": frame.source_kind,
            "sourceId": frame.source_id,
            "sequence": frame.sequence,
            "segmentId": frame.segment_id,
            "revision": frame.revision,
            "terminalId": frame.terminal_id,
            "sourceGeneration": frame.source_generation,
            "acceptedAtMs": _now_ms(),
        }}

    def _mark_terminal_accepted(self, frame: AudioFrame) -> None:
        if not frame.terminal_id:
            return
        key = self._session_source_key(frame.session_id, frame.source_kind)
        with self._terminal_lock:
            accepted = self._accepted_terminal_ids.setdefault(key, {})
            accepted[frame.terminal_id] = _now_ms()
            if len(accepted) > 256:
                for terminal_id, _accepted_at_ms in sorted(accepted.items(), key=lambda item: item[1])[:-128]:
                    accepted.pop(terminal_id, None)

    def _process_prepared_audio_frame(self, prepared: dict[str, object]) -> list[dict[str, object]]:
        early_events = prepared.get("early_events")
        if isinstance(early_events, list):
            return early_events
        publisher_for_control = prepared.get("publisher")
        if isinstance(publisher_for_control, RealtimePublisherRecord) and self.capture_control_state(session_id=publisher_for_control.session_id) == "paused":
            return []
        publisher = prepared["publisher"]
        frame = prepared["frame"]
        pending_receipt = prepared["pending_receipt"]
        counter_bucket = prepared["counter_bucket"]
        ingest_received_at_ms = int(prepared["ingest_received_at_ms"])
        queue_enter_at_ms = int(prepared.get("queue_enter_at_ms", ingest_received_at_ms))
        captured_at_ms = int(prepared["captured_at_ms"])
        sent_at_ms = prepared.get("sent_at_ms")
        source_kind = prepared["source_kind"]
        assert isinstance(publisher, RealtimePublisherRecord)
        assert isinstance(frame, AudioFrame)
        assert isinstance(pending_receipt, RealtimeFrameReceiptRecord)
        assert isinstance(counter_bucket, dict)
        assert isinstance(source_kind, str)
        events: list[dict[str, object]] = []
        queue_depth = self._active_request_enter(session_id=publisher.session_id, source_kind=source_kind)
        worker_dequeued_at_ms = _now_ms()
        self._observe_trace(frame.trace_id, queueLeaveAtMs=worker_dequeued_at_ms)
        counter_bucket["framesConsumed"] = int(counter_bucket.get("framesConsumed", 0)) + 1
        wait_samples = self._queue_wait_samples.setdefault(
            (publisher.session_id, source_kind), deque(maxlen=512)  # type: ignore[arg-type]
        )
        wait_samples.append(max(0, worker_dequeued_at_ms - queue_enter_at_ms))
        asr_started_at_ms = worker_dequeued_at_ms
        try:
            transcript, transcript_result = self._transcribe_frame(publisher=publisher, frame=frame)
            self.repository.save_frame_receipt(replace(pending_receipt, asr_status="accepted"))
        except DomainRequestError as exc:
            self._submit_cold(self._record_speech_usage,
                publisher=publisher,
                frame=frame,
                result=None,
                final_latency_ms=max(0, _now_ms() - asr_started_at_ms),
                safe_error_code=exc.error_code or "asr-failed",
            )
            self.repository.save_frame_receipt(replace(pending_receipt, asr_status="failed", error_code=exc.error_code or "asr-failed"))
            events.append(self._event_payload(self._save_event(
                session_id=publisher.session_id,
                owner_user_id=publisher.owner_user_id,
                kind="degraded",
                payload={
                    "reason": "asr-frame-failed",
                    "sourceKind": source_kind,
                    "errorCode": exc.error_code or "asr-failed",
                    "message": str(exc),
                },
            )))
            return events
        finally:
            self._active_request_leave(session_id=publisher.session_id, source_kind=source_kind)
            self._counter_bucket(session_id=publisher.session_id, source_kind=source_kind)["queueDepth"] = max(0, queue_depth - 1)
        published_at_ms = _now_ms()
        timing = {
            **{
                key: value
                for key, value in frame.diagnostics.items()
                if value is None or isinstance(value, (str, int, float, bool))
            },
            "traceId": frame.trace_id,
            "sessionId": publisher.session_id,
            "channel": source_kind,
            "sequence": frame.sequence,
            "revision": frame.revision,
            "utteranceId": frame.segment_id,
            "captureToSendMs": (max(0, int(sent_at_ms) - captured_at_ms) if isinstance(sent_at_ms, int) else None),
            "sendToIngestMs": (max(0, ingest_received_at_ms - int(sent_at_ms)) if isinstance(sent_at_ms, int) else None),
            "captureToIngestMs": max(0, ingest_received_at_ms - captured_at_ms),
            "queueWaitMs": max(0, worker_dequeued_at_ms - queue_enter_at_ms),
            "asrTtftMs": (max(0, transcript_result.first_text_at_ms - asr_started_at_ms) if transcript_result.first_text_at_ms is not None else None),
            "finalTranscriptMs": (max(0, transcript_result.completed_at_ms - asr_started_at_ms) if transcript_result.completed_at_ms is not None else None),
            "stopToTerminalMs": (max(0, published_at_ms - frame.ended_at_ms) if frame.is_final else None),
            "backendPushMs": max(0, published_at_ms - (transcript_result.completed_at_ms or asr_started_at_ms)),
            "captureToPublishMs": max(0, published_at_ms - captured_at_ms),
            "frontendRenderMs": None,
            "speechStartAtMs": frame.started_at_ms,
            "systemVadTriggerAtMs": frame.vad_triggered_at_ms if source_kind == "system" else None,
            "systemSpeechStartAtMs": frame.speech_confirmed_at_ms if source_kind == "system" else None,
            "systemFirstEffectivePartialAtMs": (
                transcript_result.partial_received_at_ms if source_kind == "system" and transcript is not None and not frame.is_final else None
            ),
            "framesBeforeFirstPartial": frame.revision if transcript is not None and not frame.is_final else None,
            "desktopAudioCaptureAtMs": captured_at_ms,
            "desktopWsSendAtMs": int(sent_at_ms) if isinstance(sent_at_ms, int) else None,
            "backendWsReceiveAtMs": ingest_received_at_ms,
            "queueEnterAtMs": queue_enter_at_ms,
            "queueLeaveAtMs": worker_dequeued_at_ms,
            "qwenAudioAppendAtMs": transcript_result.audio_appended_at_ms,
            "qwenPartialReceivedAtMs": transcript_result.partial_received_at_ms,
            "qwenFinalReceivedAtMs": transcript_result.completed_at_ms if frame.is_final else None,
            "providerResultReceivedAtMs": (
                transcript_result.completed_at_ms if frame.is_final else transcript_result.partial_received_at_ms
            ),
            "redisEventXaddAtMs": None,
            "redisEventXreadAtMs": None,
            "sseEventSendAtMs": None,
            "browserEventReceiveAtMs": None,
            "browserStateUpdateAtMs": None,
            "browserRenderAtMs": None,
            "speechEndDetectedAtMs": frame.ended_at_ms if frame.is_final else None,
            "manualCommitSentAtMs": transcript_result.commit_sent_at_ms,
            "asrSessionLockWaitStartAtMs": transcript_result.asr_lock_wait_start_at_ms,
            "asrSessionLockAcquiredAtMs": transcript_result.asr_lock_acquired_at_ms,
            "qwenSendEnqueueAtMs": transcript_result.qwen_send_enqueue_at_ms,
            "qwenWsSendStartAtMs": transcript_result.qwen_ws_send_start_at_ms,
            "qwenWsSendCompleteAtMs": transcript_result.qwen_ws_send_complete_at_ms,
            "coalescedFrameCount": int(prepared.get("coalesced_frame_count", 1)),
            "connectionId": transcript_result.connection_id,
        }
        self._observe_trace(frame.trace_id, **timing)
        self._set_latest_timing(session_id=publisher.session_id, source_kind=source_kind, timing=timing)
        self._submit_cold(self._record_speech_usage,
            publisher=publisher,
            frame=frame,
            result=transcript_result,
            final_latency_ms=timing["finalTranscriptMs"],
        )
        if transcript is None:
            if transcript_result.suppressed_reason == "empty-transcript":
                counter_bucket["emptyResultsSuppressed"] += 1
                if not frame.is_final:
                    counter_bucket["phantomResultsSuppressed"] += 1
                return events
            if transcript_result.suppressed_reason == "filler-transcript":
                counter_bucket["fillerResultsSuppressed"] += 1
                events.append(self._event_payload(self._save_event(
                    session_id=publisher.session_id,
                    owner_user_id=publisher.owner_user_id,
                    kind="degraded",
                    payload={
                        "reason": "filler-transcript-suppressed",
                        "sourceKind": source_kind,
                        "message": "检测到纯语气音，系统已忽略本段结果。",
                    },
                )))
            if transcript_result.suppressed_reason == "repetitive-transcript":
                counter_bucket["repetitiveResultsSuppressed"] += 1
                events.append(self._event_payload(self._save_event(
                    session_id=publisher.session_id,
                    owner_user_id=publisher.owner_user_id,
                    kind="degraded",
                    payload={
                        "reason": "repetitive-transcript-suppressed",
                        "sourceKind": source_kind,
                        "message": "检测到异常重复转写，系统已忽略本段结果。",
                    },
                )))
            if transcript_result.suppressed_reason in {"duplicate-nearby-transcript", "cross-channel-duplicate-transcript"}:
                counter_bucket["duplicateResultsSuppressed"] += 1
                cross_channel = transcript_result.suppressed_reason == "cross-channel-duplicate-transcript"
                events.append(self._event_payload(self._save_event(
                    session_id=publisher.session_id,
                    owner_user_id=publisher.owner_user_id,
                    kind="degraded",
                    payload={
                        "reason": "cross-channel-echo-suppressed" if cross_channel else "duplicate-nearby-transcript-suppressed",
                        "sourceKind": source_kind,
                        "message": "检测到跨声道回声，系统已保留主通道并忽略重复片段。" if cross_channel else "检测到短时间内高度重复的转写，系统已忽略本段结果。",
                    },
                )))
            return events
        transcript = self.repository.save_transcript(replace(transcript, published_at_ms=published_at_ms, performance=timing))
        if not self._is_meaningful_transcript(transcript.text):
            counter_bucket["emptyResultsSuppressed"] += 1
            if not frame.is_final:
                counter_bucket["phantomResultsSuppressed"] += 1
            return events
        events.append(self._event_payload(self._save_event(
            session_id=publisher.session_id,
            owner_user_id=publisher.owner_user_id,
            kind="transcript-updated",
            payload={
                "segmentId": transcript.segment_id,
                "sourceId": transcript.source_id,
                "sourceKind": transcript.source_kind,
                "revision": transcript.revision,
                "role": transcript.role,
                "text": transcript.text,
                "transcriptConfidence": transcript.transcript_confidence,
                "startedAtMs": transcript.started_at_ms,
                "endedAtMs": transcript.ended_at_ms,
                "isFinal": transcript.is_final,
                "overlap": transcript.overlap,
                "terminalState": transcript.terminal_state,
                "finalizationReason": transcript.finalization_reason,
                "publishedAtMs": transcript.published_at_ms,
                "performance": transcript.performance,
            },
        )))
        stable_event = self._observe_stable_interviewer_partial(transcript)
        if transcript.is_final:
            self._submit_cold(self.repository.persist_transcript, transcript)
        if transcript.usage is not None:
            self._submit_cold(self.session_service.record_usage,
                user_id=publisher.owner_user_id,
                session_id=publisher.session_id,
                usage_kind="other",
                prompt_tokens=0,
                completion_tokens=0,
                total_tokens=transcript.usage.total_tokens,
                provider_name=transcript.usage.provider_name,
                model_name=transcript.usage.model_name,
                related_task_id=transcript.segment_id,
            )
        if transcript.is_final and transcript.terminal_state != "incomplete":
            self._submit_cold(self.session_service.append_context,
                user_id=publisher.owner_user_id,
                session_id=publisher.session_id,
                role=transcript.role,
                source_kind=f"realtime-{transcript.source_kind}",
                content=transcript.text,
                visibility="session",
                related_task_id=transcript.segment_id,
            )
            candidate = self._maybe_detect_question(transcript=transcript)
            if candidate is not None:
                events.append(self._event_payload(self._save_event(
                    session_id=publisher.session_id,
                    owner_user_id=publisher.owner_user_id,
                    kind="question-candidate" if candidate.state == "needs-confirmation" else "question-confirmed",
                    payload={
                        "candidateId": candidate.candidate_id,
                        "state": candidate.state,
                        "text": candidate.text,
                        "confidence": candidate.confidence,
                        "candidate": self._candidate_response(candidate).model_dump(by_alias=True),
                    },
                )))
        # Keep the established transcript -> question event order for released
        # clients. Stable-question is additive and is delivered afterwards.
        if stable_event is not None:
            events.append(self._event_payload(stable_event))
        return events

    def confirm_candidate(self, *, user_id: str, candidate_id: str) -> QuestionCandidateRecord:
        candidate = self._require_candidate(user_id=user_id, candidate_id=candidate_id)
        if candidate.state != "needs-confirmation":
            return candidate
        confirmed = self.repository.save_candidate(
            replace(candidate, state="confirmed", reason="user-confirmed", updated_at_ms=_now_ms())
        )
        self._save_event(
            session_id=confirmed.session_id,
            owner_user_id=user_id,
            kind="question-confirmed",
            payload={"candidateId": confirmed.candidate_id, "text": confirmed.text},
        )
        return confirmed

    def dismiss_candidate(self, *, user_id: str, candidate_id: str) -> QuestionCandidateRecord:
        candidate = self._require_candidate(user_id=user_id, candidate_id=candidate_id)
        dismissed = self.repository.save_candidate(replace(candidate, state="dismissed", reason="user-dismissed", updated_at_ms=_now_ms()))
        self._save_event(
            session_id=dismissed.session_id,
            owner_user_id=user_id,
            kind="question-candidate",
            payload={"candidateId": dismissed.candidate_id, "state": dismissed.state, "text": dismissed.text},
        )
        return dismissed

    def get_runtime(self, *, user_id: str, session_id: str) -> RealtimeSessionRuntimeResponse:
        session = self.session_service.get_session(user_id=user_id, session_id=session_id)
        capture_state = self.capture_control_state(session_id=session_id) if session.status == "live" else "ready"
        binding = self.repository.get_session_desktop_binding(user_id=user_id, session_id=session_id)
        device = self.repository.get_desktop_device_by_code(binding.manual_code) if binding is not None else None
        publishers = [item for item in self.repository.list_publishers_for_session(session_id=session_id) if item.owner_user_id == user_id]
        transcripts = [item for item in self.repository.list_transcripts_for_session(session_id=session_id) if item.owner_user_id == user_id]
        candidates = [item for item in self.repository.list_candidates_for_session(session_id=session_id) if item.owner_user_id == user_id]
        events = [
            item
            for item in self.repository.list_latest_events_for_session(
                session_id=session_id,
                kinds={"device-status", "degraded"},
            )
            if item.owner_user_id == user_id
        ]
        latest_device_status = next((item for item in reversed(events) if item.kind == "device-status"), None)
        web_heartbeat = self.repository.get_web_session_heartbeat(user_id=user_id, session_id=session_id)
        raw_health = latest_device_status.payload.get("sourceHealth", []) if latest_device_status is not None else []
        source_health = [self._runtime_source_health(item) for item in raw_health if isinstance(item, dict)]
        source_health_by_kind = {item.source_kind: item for item in source_health}
        receipts = [item for item in self.repository.list_frame_receipts_for_session(session_id=session_id) if item.owner_user_id == user_id]
        latest_state = publishers[-1].status if publishers else None
        last_degraded = next((item for item in reversed(events) if item.kind == "degraded"), None)
        last_failed_receipt = next((item for item in reversed(receipts) if item.asr_status == "failed"), None)
        last_error_code = (
            str(last_degraded.payload.get("errorCode") or last_degraded.payload.get("reason"))
            if last_degraded else
            str(last_failed_receipt.error_code)
            if last_failed_receipt and last_failed_receipt.error_code is not None
            else None
        )
        if binding is None:
            stage = "registered"
        elif session.status != "live":
            stage = "bound"
        elif capture_state == "paused":
            stage = "paused"
        elif any(item.status in {"transcribing"} for item in publishers):
            stage = "transcribing"
        elif transcripts:
            stage = "web-visible"
        elif receipts:
            stage = "publishing"
        elif latest_state in {"failed", "degraded"}:
            stage = latest_state
        else:
            stage = "live"
        counters_by_source: dict[str, RealtimeRuntimeCountersResponse] = {}
        latest_by_source: dict[str, RealtimeStageTimingResponse] = {}
        for source_kind in ("microphone", "system"):
            counter_bucket = self._counter_bucket(session_id=session_id, source_kind=source_kind)  # type: ignore[arg-type]
            diagnostics = self._gateway_diagnostics(source_kind=source_kind)  # type: ignore[arg-type]
            runtime_status = self._gateway_runtime_status(source_kind=source_kind)  # type: ignore[arg-type]
            counter_bucket["connectionRecreations"] = diagnostics.get("connection_recreations", counter_bucket.get("connectionRecreations", 0))
            counter_bucket["providerAppendCount"] = diagnostics.get("append_count", 0)
            counter_bucket["providerCommitCount"] = diagnostics.get("commit_count", 0)
            counter_bucket["providerCompletedMissing"] = diagnostics.get("completed_missing", 0)
            counter_bucket["blankPartialSuppressed"] = diagnostics.get("blank_partial_suppressed", 0)
            counter_bucket["vadToManualFallbacks"] = diagnostics.get("vad_to_manual_fallbacks", 0)
            counter_bucket["idleProviderSessionClosures"] = diagnostics.get("idle_session_closures", 0)
            counter_bucket["activeProviderSessions"] = diagnostics.get("active_provider_sessions", 0)
            counter_bucket["asrConnectionCreateCount"] = diagnostics.get("asr_connection_create_count", 0)
            counter_bucket["asrConnectionReconnectCount"] = diagnostics.get("asr_connection_reconnect_count", 0)
            counter_bucket["asrConnectionLifetimeMs"] = diagnostics.get("asr_connection_lifetime_ms", 0)
            counter_bucket["utteranceCount"] = diagnostics.get("utterance_count", 0)
            counter_bucket["utterancesPerConnection"] = diagnostics.get("utterances_per_connection", 0.0)
            counters_by_source[source_kind] = RealtimeRuntimeCountersResponse(**counter_bucket)
            latest_timing = self._latest_timing(session_id=session_id, source_kind=source_kind)  # type: ignore[arg-type]
            if latest_timing is not None:
                latest_by_source[source_kind] = RealtimeStageTimingResponse(**latest_timing)
            existing_health = source_health_by_kind.get(source_kind)
            if existing_health is not None:
                updated_health = existing_health.model_copy(update={
                    "provider_mode": runtime_status.get("mode"),
                    "provider_connection_state": runtime_status.get("connection_state"),
                    "provider_error_code": runtime_status.get("last_error_code"),
                })
                source_health[source_health.index(existing_health)] = updated_health
        evidence = self._runtime_evidence(
            session_status=session.status,
            binding_present=binding is not None,
            publishers=publishers,
            source_health=source_health,
            receipts=receipts,
            transcripts=transcripts,
            web_heartbeat=web_heartbeat,
        )
        anomaly_reasons, dominant_bottleneck = self._classify_runtime_anomalies(
            session_status=session.status,
            machine_code_bound=binding is not None,
            source_health=source_health,
            receipts=receipts,
            latest_by_source=latest_by_source,
            counters_by_source=counters_by_source,
            latest_state=latest_state,
            last_error_code=last_error_code,
            evidence=evidence,
        )
        if capture_state == "paused":
            anomaly_reasons, dominant_bottleneck = [], None
        return RealtimeSessionRuntimeResponse(
            sessionId=session_id,
            sessionStatus=session.status,
            stage=stage,
            backendReachable=True,
            deviceRegistered=device is not None,
            machineCodeBound=binding is not None,
            sessionLive=session.status == "live",
            captureState=capture_state,
            manualCode=binding.manual_code if binding else None,
            deviceId=binding.device_id if binding else None,
            displayName=binding.display_name if binding else None,
            publishers=[self._publisher_response(item) for item in publishers],
            sourceHealth=source_health,
            frameReceipts=[RealtimeFrameReceiptResponse(
                sourceKind=item.source_kind,
                sourceId=item.source_id,
                frameCount=item.frame_count,
                lastFrameAtMs=item.received_at_ms,
                lastSequence=item.sequence,
                lastAsrStatus=item.asr_status,
                lastErrorCode=item.error_code,
            ) for item in receipts],
            transcriptCount=len(transcripts),
            questionCandidateCount=len(candidates),
            latestState=latest_state,
            lastErrorCode=last_error_code,
            anomalyReasons=anomaly_reasons,
            dominantBottleneck=dominant_bottleneck,
            performance=RealtimeRuntimePerformanceResponse(
                latestBySource=latest_by_source,
                countersBySource=counters_by_source,
            ),
            evidence=evidence,
            updatedAtMs=_now_ms(),
        )

    def _classify_runtime_anomalies(
        self,
        *,
        session_status: str,
        machine_code_bound: bool,
        source_health: list[RealtimeSourceHealthResponse],
        receipts: list[RealtimeFrameReceiptRecord],
        latest_by_source: dict[str, RealtimeStageTimingResponse],
        counters_by_source: dict[str, RealtimeRuntimeCountersResponse],
        latest_state: str | None,
        last_error_code: str | None,
        evidence: dict[str, object],
    ) -> tuple[list[str], str | None]:
        reasons: list[str] = []
        if not machine_code_bound:
            return ["machine_code_not_bound"], "machine_code_not_bound"
        if session_status != "live":
            return ["session_not_live"], "session_not_live"
        if evidence.get("sessionLive") and not evidence.get("localSignalObserved") and not evidence.get("realFrameReceiptReceived"):
            reasons.append("desktop_no_audio_frames")
        if evidence.get("localSignalObserved") and not evidence.get("realFrameReceiptReceived"):
            reasons.append("backend-no-receipt")
        if not evidence.get("localSignalObserved") and not evidence.get("realFrameReceiptReceived"):
            reasons.append("capture-no-frame")
        if not evidence.get("publisherCreated"):
            reasons.append("publisher-no-connect")
        if evidence.get("transcriptEmitted") and not evidence.get("webConsumerSeen"):
            reasons.append("web-no-consumer")
        for health in source_health:
            if (health.oldest_pending_frame_age_ms or 0) > 300 or (health.pending_frame_count or 0) > 8:
                reasons.append(f"{health.source_kind}:desktop_send_backlog")
            if (health.dropped_frame_count or 0) > 0:
                reasons.append(f"{health.source_kind}:desktop_audio_gap")
        for source_kind, timing in latest_by_source.items():
            if (timing.capture_to_send_ms or 0) > 180:
                reasons.append(f"{source_kind}:desktop_send_backlog")
            if (timing.queue_wait_ms or 0) > 120:
                reasons.append(f"{source_kind}:backend_ingest_queue_delayed")
            if (timing.asr_ttft_ms or 0) > 700:
                reasons.append(f"{source_kind}:provider_partial_timeout")
            if (timing.final_transcript_ms or 0) > 1600:
                reasons.append(f"{source_kind}:provider_final_timeout")
            if (timing.backend_push_ms or 0) > 250:
                reasons.append(f"{source_kind}:publish_lag")
        suppression_reasons: list[str] = []
        for source_kind, counters in counters_by_source.items():
            if counters.filler_results_suppressed > 0:
                suppression_reasons.append(f"{source_kind}:filler_transcript_suppressed")
            if counters.repetitive_results_suppressed > 0:
                suppression_reasons.append(f"{source_kind}:repetitive_transcript_suppressed")
            if counters.duplicate_results_suppressed > 0:
                suppression_reasons.append(f"{source_kind}:duplicate_transcript_suppressed")
        if suppression_reasons:
            reasons.extend(suppression_reasons)
        if evidence.get("asrAccepted") and not evidence.get("transcriptEmitted"):
            # Keep this as lower-priority than suppression counters; it is a provider-signal anomaly
            # and should not hide root-cause like repetitive suppression.
            reasons.append("asr-accepted-no-text")
        if latest_state == "failed" or (last_error_code is not None and "asr" in last_error_code):
            reasons.append("provider_failed")
        return reasons, (reasons[0] if reasons else None)


    def _runtime_evidence(
        self,
        *,
        session_status: str,
        binding_present: bool,
        publishers: list[RealtimePublisherRecord],
        source_health: list[RealtimeSourceHealthResponse],
        receipts: list[RealtimeFrameReceiptRecord],
        transcripts: list[TranscriptSegmentRecord],
        web_heartbeat: WebSessionHeartbeatRecord | None,
    ) -> dict[str, object]:
        real_receipts = [item for item in receipts if item.source_id != "diagnostic-pcm-probe" and item.frame_count > 0]
        diagnostic_receipts = [item for item in receipts if item.source_id == "diagnostic-pcm-probe" and item.frame_count > 0]
        local_signal_sources = [
            item.source_kind for item in source_health
            if (item.level or 0) > 0 or item.last_signal_at_ms is not None or (item.frame_count or 0) > 0
        ]
        real_frame_sources = sorted({item.source_kind for item in real_receipts})
        accepted_sources = sorted({item.source_kind for item in receipts if item.asr_status == "accepted"})
        return {
            "bindingReady": binding_present,
            "sessionLive": session_status == "live",
            "publisherCreated": len(publishers) > 0,
            "publisherCount": len(publishers),
            "localSignalObserved": len(local_signal_sources) > 0,
            "localSignalSources": sorted(set(local_signal_sources)),
            "realFrameReceiptReceived": len(real_receipts) > 0,
            "realFrameSources": real_frame_sources,
            "diagnosticProbeFrameReceived": len(diagnostic_receipts) > 0,
            "asrAccepted": any(item.asr_status == "accepted" for item in receipts),
            "asrAcceptedSources": accepted_sources,
            "transcriptEmitted": len(transcripts) > 0,
            "transcriptCount": len(transcripts),
            "webConsumerSeen": web_heartbeat is not None and web_heartbeat.page == "live",
            "webConsumerLastSeenAtMs": web_heartbeat.seen_at_ms if web_heartbeat else None,
        }

    def list_transcripts(self, *, user_id: str, session_id: str) -> RealtimeTranscriptListResponse:
        self.session_service.get_session(user_id=user_id, session_id=session_id)
        transcripts = [item for item in self.repository.list_transcripts_for_session(session_id=session_id) if item.owner_user_id == user_id]
        return RealtimeTranscriptListResponse(sessionId=session_id, transcripts=[self._transcript_response(item) for item in transcripts])

    def list_candidates(self, *, user_id: str, session_id: str):
        self.session_service.get_session(user_id=user_id, session_id=session_id)
        candidates = [item for item in self.repository.list_candidates_for_session(session_id=session_id) if item.owner_user_id == user_id]
        return RealtimeQuestionCandidateListResponse(sessionId=session_id, candidates=[self._candidate_response(item) for item in candidates])

    def list_events(self, *, user_id: str, session_id: str):
        self.session_service.get_session(user_id=user_id, session_id=session_id)
        events = [item for item in self.repository.list_events_for_session(session_id=session_id) if item.owner_user_id == user_id]
        return RealtimeEventListResponse(
            sessionId=session_id,
            events=[self.event_response(item) for item in events],
        )

    def get_session_snapshot(self, *, user_id: str, session_id: str) -> RealtimeSessionSnapshotResponse:
        """Return one authoritative recovery payload without changing legacy list endpoints."""
        runtime = self.get_runtime(user_id=user_id, session_id=session_id)
        transcripts = self.list_transcripts(user_id=user_id, session_id=session_id)
        candidates = self.list_candidates(user_id=user_id, session_id=session_id)
        events = self.list_events(user_id=user_id, session_id=session_id)
        cursor, _incremental, resumable = self.list_session_events_after(
            user_id=user_id,
            session_id=session_id,
            cursor=0,
        )
        return RealtimeSessionSnapshotResponse(
            sessionId=session_id,
            ownerUserId=user_id,
            cursor=cursor,
            resumable=resumable,
            transcripts=transcripts,
            candidates=candidates,
            events=events,
            runtime=runtime,
        )

    @staticmethod
    def event_response(event: RealtimeEvent) -> RealtimeEventResponse:
        return RealtimeEventResponse(
            eventId=event.event_id,
            kind=event.kind,
            payload=event.payload,
            createdAtMs=event.created_at_ms,
        )

    def publish_screenshot_shortcut_accepted(self, *, user_id: str, session_id: str, request_id: str) -> RealtimeEventResponse:
        self.session_service.get_session(user_id=user_id, session_id=session_id)
        event = self._save_event(
            session_id=session_id,
            owner_user_id=user_id,
            kind="screenshot-shortcut-accepted",
            payload={"requestId": request_id, "status": "requested"},
        )
        return RealtimeEventResponse(eventId=event.event_id, kind=event.kind, payload=event.payload, createdAtMs=event.created_at_ms)

    def session_activity_version(self, *, user_id: str, session_id: str) -> int:
        self.session_service.get_session(user_id=user_id, session_id=session_id)
        return self.repository.get_session_activity_version(session_id=session_id)

    def publish_device_status(
        self,
        *,
        user_id: str,
        session_id: str,
        device_id: str,
        capture_state: str,
        source_health: list[dict[str, object]],
        capabilities: dict[str, object],
    ) -> RealtimeEventResponse:
        self.session_service.get_session(user_id=user_id, session_id=session_id)
        safe_source_health = [
            {
                "sourceId": str(item.get("sourceId", "")),
                "sourceKind": str(item.get("sourceKind", "")),
                "label": str(item.get("label", ""))[:120],
                "state": str(item.get("state", "")),
                "stage": item.get("stage"),
                "level": float(item.get("level", 0) or 0),
                "lastSignalAtMs": item.get("lastSignalAtMs"),
                "frameCount": item.get("frameCount"),
                "lastFrameAtMs": item.get("lastFrameAtMs"),
                "backendFrameCount": item.get("backendFrameCount"),
                "lastBackendFrameAtMs": item.get("lastBackendFrameAtMs"),
                "pendingFrameCount": item.get("pendingFrameCount"),
                "oldestPendingFrameAgeMs": item.get("oldestPendingFrameAgeMs"),
                "droppedFrameCount": item.get("droppedFrameCount"),
                "reconnectCount": item.get("reconnectCount"),
                "lastAckAtMs": item.get("lastAckAtMs"),
                "lastReconnectReason": item.get("lastReconnectReason"),
                "noiseFloor": item.get("noiseFloor"),
                "captureProcessor": item.get("captureProcessor"),
                "endpointingMode": item.get("endpointingMode"),
                "turnState": item.get("turnState"),
                "finalizationReason": item.get("finalizationReason"),
                "sourceGeneration": item.get("sourceGeneration"),
                "terminalPendingSinceMs": item.get("terminalPendingSinceMs"),
                "terminalAgeMs": item.get("terminalAgeMs"),
                "terminalResendCount": item.get("terminalResendCount"),
                "terminalAckAtMs": item.get("terminalAckAtMs"),
                "errorCode": item.get("errorCode"),
            }
            for item in source_health
        ]
        event = self._save_event(
            session_id=session_id,
            owner_user_id=user_id,
            kind="device-status",
            payload={
                "deviceId": device_id,
                "captureState": capture_state,
                "sourceHealth": safe_source_health,
                "capabilities": {
                    "platform": capabilities.get("platform"),
                    "architecture": capabilities.get("architecture"),
                    "protocolVersion": capabilities.get("protocolVersion"),
                    "appVersion": capabilities.get("appVersion"),
                    "microphone": capabilities.get("microphone"),
                    "systemAudio": capabilities.get("systemAudio"),
                },
            },
        )
        return RealtimeEventResponse(eventId=event.event_id, kind=event.kind, payload=event.payload, createdAtMs=event.created_at_ms)

    def _transcribe_frame(self, *, publisher: RealtimePublisherRecord, frame: AudioFrame) -> tuple[TranscriptSegmentRecord | None, TranscriptResult]:
        role = "candidate" if frame.source_kind == "microphone" else "interviewer"
        last_error: Exception | None = None
        asr_timeout_seconds = self._asr_timeout_seconds(frame)
        for attempt in range(self.settings.realtime_asr_retry_max_attempts + 1):
            try:
                provider_operation = (
                    getattr(self.asr_gateway, "finalize", self.asr_gateway.transcribe)
                    if frame.is_final
                    else self.asr_gateway.transcribe
                )
                if not self._asr_slots.acquire(timeout=asr_timeout_seconds):
                    raise RetryableAsrError("asr_capacity_timeout")
                try:
                    future = self._asr_executor.submit(provider_operation, frame=frame, attempt=attempt)
                    future.add_done_callback(lambda _future: self._asr_slots.release())
                except RuntimeError:
                    self._asr_slots.release()
                    raise
                try:
                    result = future.result(timeout=asr_timeout_seconds)
                except concurrent.futures.TimeoutError as exc:
                    future.cancel()
                    self._close_asr_source(session_id=frame.session_id, source_kind=frame.source_kind)
                    self._log(logging.WARNING, "realtime_speech.transcribe_timeout", session_id=publisher.session_id, publisher_id=publisher.publisher_id, state="transcribe-timeout", error_code="realtime_asr_frame_timeout")
                    raise RetryableAsrError("realtime_asr_frame_timeout") from exc
                suppression_reason = self._suppression_reason(result.text, frame=frame)
                if suppression_reason is None:
                    suppression_reason = self._duplicate_nearby_suppression_reason(
                        text=result.text,
                        publisher=publisher,
                        frame=frame,
                    )
                if suppression_reason is not None:
                    if frame.is_final:
                        self._finalize_suppressed_partial(
                            publisher=publisher,
                            frame=frame,
                            result=result,
                        )
                    return None, replace(result, suppressed_reason=suppression_reason)
                current = self.repository.get_transcript(frame.session_id, frame.segment_id)
                created_at_ms = current.created_at_ms if current is not None else _now_ms()
                published_at_ms = _now_ms()
                performance = {
                    "traceId": frame.trace_id,
                    "captureToSendMs": (max(0, frame.sent_at_ms - frame.captured_at_ms) if frame.sent_at_ms is not None else None),
                    "sendToIngestMs": None,
                    "captureToIngestMs": None,
                    "queueWaitMs": None,
                    "asrTtftMs": None,
                    "finalTranscriptMs": None,
                    "stopToTerminalMs": None,
                    "backendPushMs": None,
                    "captureToPublishMs": max(0, published_at_ms - frame.captured_at_ms),
                    "frontendRenderMs": None,
                }
                stored = TranscriptSegmentRecord(
                    segment_id=frame.segment_id,
                    session_id=frame.session_id,
                    owner_user_id=publisher.owner_user_id,
                    source_id=frame.source_id,
                    source_kind=frame.source_kind,
                    role=role,  # type: ignore[arg-type]
                    revision=max(frame.revision, current.revision + 1 if current is not None else frame.revision),
                    text=result.text,
                    transcript_confidence=result.confidence,
                    started_at_ms=frame.started_at_ms,
                    ended_at_ms=frame.ended_at_ms,
                    is_final=frame.is_final,
                    overlap=result.overlap,
                    created_at_ms=created_at_ms,
                    terminal_state=("final" if frame.is_final else None),
                    finalization_reason=(frame.finalization_reason if frame.is_final else None),
                    published_at_ms=published_at_ms,
                    performance=performance,
                    usage=result.usage,
                )
                return stored, result
            except RetryableAsrError as exc:
                self._log(logging.WARNING, "realtime_speech.transcribe_retry", session_id=publisher.session_id, publisher_id=publisher.publisher_id, state="transcribe-retry", error_code=str(exc))
                last_error = exc
                if str(exc) == "realtime_asr_frame_timeout":
                    break
                if attempt < self.settings.realtime_asr_retry_max_attempts:
                    sleep(min(0.35, (0.04 * (2 ** attempt)) + random.uniform(0.0, 0.025)))
                continue
            except NonRetryableAsrError as exc:
                self._log(logging.WARNING, "realtime_speech.transcribe_non_retryable", session_id=publisher.session_id, publisher_id=publisher.publisher_id, state="transcribe-failed", error_code=str(exc))
                last_error = exc
                break
            except Exception as exc:
                self._log(logging.ERROR, "realtime_speech.transcribe_error", session_id=publisher.session_id, publisher_id=publisher.publisher_id, state="transcribe-error", error_code=str(exc))
                last_error = exc
                break
        degraded = self._transition_publisher_status(publisher, "degraded")
        self._save_event(
            session_id=degraded.session_id,
            owner_user_id=degraded.owner_user_id,
            kind="degraded",
            payload={"publisherId": degraded.publisher_id, "reason": "asr-failed", "errorCode": last_error.__class__.__name__ if last_error else "asr_failed"},
        )
        error_code = str(last_error) if last_error and str(last_error).strip() else "asr-failed"
        raise DomainRequestError("realtime-speech", "transcribe", "实时语音转写失败。", 502, error_code=error_code)

    def _close_asr_source(self, *, session_id: str, source_kind: RealtimeSourceKind) -> int:
        close_source = getattr(self.asr_gateway, "close_source", None)
        if callable(close_source):
            closed = int(close_source(session_id=session_id, source_kind=source_kind))
        else:
            # Compatibility for third-party/test adapters predating source-scoped recovery.
            closed = int(self.asr_gateway.close_session(session_id=session_id))
        bucket = self._counter_bucket(session_id=session_id, source_kind=source_kind)
        bucket["sourceReconnects"] = int(bucket.get("sourceReconnects", 0)) + max(1, closed)
        return closed

    def _finalize_suppressed_partial(
        self,
        *,
        publisher: RealtimePublisherRecord,
        frame: AudioFrame,
        result: TranscriptResult,
    ) -> None:
        """Close an already-visible partial without business side effects."""
        current = self.repository.get_transcript(frame.session_id, frame.segment_id)
        if current is None or current.is_final:
            return
        self.repository.save_transcript(replace(
            current,
            revision=max(frame.revision, current.revision + 1),
            text=result.text.strip() or current.text,
            transcript_confidence=result.confidence,
            ended_at_ms=max(current.ended_at_ms, frame.ended_at_ms),
            is_final=True,
            overlap=result.overlap,
            published_at_ms=_now_ms(),
            usage=None,
        ))

    def _reset_realtime_session(self, *, session_id: str, retired: bool) -> None:
        if retired:
            self._stop_realtime_metering(session_id=session_id)
        self.asr_gateway.close_session(session_id=session_id)
        with self._frame_worker_lock:
            if retired:
                self._retired_session_ids.add(session_id)
            else:
                self._retired_session_ids.discard(session_id)
            queues = [
                (key, work_queue)
                for key, work_queue in self._frame_queues.items()
                if key[0] == session_id
            ]
            for key, work_queue in queues:
                self._frame_queues.pop(key, None)
                self._frame_workers.pop(key, None)
                while True:
                    try:
                        work_queue.get_nowait()
                    except queue.Empty:
                        break
                    else:
                        work_queue.task_done()
                self._counter_bucket(session_id=key[0], source_kind=key[1])["queueDepth"] = 0
            self._active_requests_by_session_source = {
                key: value
                for key, value in self._active_requests_by_session_source.items()
                if key[0] != session_id
            }
            self._latest_timings_by_session_source = {
                key: value
                for key, value in self._latest_timings_by_session_source.items()
                if key[0] != session_id
            }
            self._queue_wait_samples = {
                key: value for key, value in self._queue_wait_samples.items() if key[0] != session_id
            }
        with self._watchdog_lock:
            self._active_source_turns = {
                key: value for key, value in self._active_source_turns.items() if key[0] != session_id
            }

    def _asr_timeout_seconds(self, frame: AudioFrame) -> float:
        configured = max(1.0, float(self.settings.realtime_asr_frame_timeout_seconds))
        if frame.is_final:
            configured = max(
                configured,
                float(self.settings.realtime_asr_finalize_timeout_seconds) + 1.0,
            )
        return min(30.0, configured)

    @staticmethod
    def _suppression_reason(text: str, *, frame: AudioFrame) -> str | None:
        if not RealtimeSpeechService._is_meaningful_transcript(text):
            return "empty-transcript"
        if RealtimeSpeechService._looks_like_filler_transcript(text, source_kind=frame.source_kind):
            return "filler-transcript"
        if RealtimeSpeechService._looks_like_repetitive_hallucination(text, source_kind=frame.source_kind):
            return "repetitive-transcript"
        return None

    @staticmethod
    def _is_meaningful_transcript(text: str) -> bool:
        compact = re.sub(r"\s+|[，。！？、；：,.!?;:~～…·]+", "", text).strip()
        return bool(compact)

    @staticmethod
    def _looks_like_filler_transcript(text: str, *, source_kind: RealtimeSourceKind) -> bool:
        compact = re.sub(r"\s+", "", text)
        compact = re.sub(r"[，。！？、；：,.!?;:~～…·]+", "", compact)
        if not compact:
            return True
        filler_tokens = (
            "嗯", "啊", "呃", "额", "唉", "诶", "欸", "哦", "喔", "哎", "哈", "嘿",
        )
        if compact in filler_tokens:
            return True
        if compact.lower() in {"system", "assistant", "test"}:
            return True
        filler_pattern = "|".join(sorted((re.escape(item) for item in filler_tokens), key=len, reverse=True))
        stripped = re.sub(f"({filler_pattern})+", "", compact)
        if not stripped and len(compact) <= 12:
            return True
        return False

    @staticmethod
    def _looks_like_repetitive_hallucination(text: str, *, source_kind: RealtimeSourceKind) -> bool:
        normalized = re.sub(r"\s+", "", text)
        normalized = re.sub(r"[，。！？、；：,.!?;:]+", "|", normalized).strip("|")
        compact = normalized.replace("|", "")
        if len(compact) < 48:
            return False
        clauses = [item for item in normalized.split("|") if item]
        if len(clauses) >= 4:
            counts: dict[str, int] = {}
            for clause in clauses:
                counts[clause] = counts.get(clause, 0) + 1
            most_common = max(counts.values())
            if len(counts) <= max(2, len(clauses) // 4) and most_common / len(clauses) >= 0.6:
                return True
            adjacent_repeat_count = 0
            for index in range(1, len(clauses)):
                previous = clauses[index - 1]
                current = clauses[index]
                shorter, longer = sorted((previous, current), key=len)
                if shorter and (current == previous or longer.count(shorter) >= 2):
                    adjacent_repeat_count += 1
            if adjacent_repeat_count >= max(2, len(clauses) // 3):
                return True
        if len(compact) >= 64:
            windows = [compact[index:index + 10] for index in range(0, max(0, len(compact) - 9), 2)]
            windows = [item for item in windows if len(item) == 10]
            if windows:
                repeated_windows = sum(1 for count in Counter(windows).values() if count >= 3)
                if repeated_windows >= max(2, len(windows) // 10):
                    return True
        if source_kind == "system":
            windows = [compact[index:index + 12] for index in range(0, max(0, len(compact) - 11), 3)]
            windows = [item for item in windows if len(item) == 12]
            if windows:
                unique_windows = len(set(windows))
                if unique_windows / len(windows) <= 0.35:
                    return True
            if len(compact) >= 96:
                clause_lengths = [len(item) for item in clauses] if clauses else [len(compact)]
                if clause_lengths and sum(clause_lengths) / len(clause_lengths) >= 12:
                    repeated_prefixes = sum(1 for index in range(1, len(clauses)) if clauses[index][:10] == clauses[index - 1][:10])
                    if repeated_prefixes >= max(2, len(clauses) // 3):
                        return True
        return False

    def _duplicate_nearby_suppression_reason(
        self,
        *,
        text: str,
        publisher: RealtimePublisherRecord,
        frame: AudioFrame,
    ) -> str | None:
        compact = self._compact_transcript_for_dedup(text)
        if len(compact) < 2:
            return None
        transcripts = [
            item for item in self.repository.list_transcripts_for_session(session_id=frame.session_id)
            if item.owner_user_id == publisher.owner_user_id
            and self._is_meaningful_transcript(item.text)
            and item.is_final
        ]
        if not transcripts:
            return None
        same_source = [item for item in transcripts if item.source_kind == frame.source_kind]
        if same_source and len(compact) <= 24:
            latest = same_source[-1]
            previous_compact = self._compact_transcript_for_dedup(latest.text)
            if previous_compact and abs(frame.started_at_ms - latest.ended_at_ms) <= 6_000:
                if compact == previous_compact:
                    return "duplicate-nearby-transcript"
                if len(compact) <= 32 and len(previous_compact) <= 32 and (compact in previous_compact or previous_compact in compact):
                    return "duplicate-nearby-transcript"
                shorter, longer = sorted((compact, previous_compact), key=len)
                if len(shorter) >= 2 and longer.count(shorter) >= 2:
                    return "duplicate-nearby-transcript"

        for previous in reversed(transcripts):
            if previous.source_kind == frame.source_kind:
                continue
            # System audio is the authoritative interviewer channel. Speaker
            # leakage can make a matching microphone final arrive first, but
            # arrival order must not suppress the later interviewer final.
            if frame.source_kind == "system":
                continue
            gap_ms = max(
                previous.started_at_ms - frame.ended_at_ms,
                frame.started_at_ms - previous.ended_at_ms,
                0,
            )
            if gap_ms > 750:
                continue
            previous_compact = self._compact_transcript_for_dedup(previous.text)
            if min(len(compact), len(previous_compact)) < 4:
                continue
            if compact == previous_compact:
                return "cross-channel-duplicate-transcript"
            shorter, longer = sorted((compact, previous_compact), key=len)
            if len(shorter) >= 6 and shorter in longer:
                return "cross-channel-duplicate-transcript"
            if SequenceMatcher(None, compact, previous_compact).ratio() >= 0.88:
                return "cross-channel-duplicate-transcript"
        return None

    @staticmethod
    def _compact_transcript_for_dedup(text: str) -> str:
        compact = re.sub(r"\s+", "", text).lower()
        return re.sub(r"[，。！？、；：,.!?;:~～…·\-—_]+", "", compact)

    @staticmethod
    def _runtime_source_health(item: dict[str, object]) -> RealtimeSourceHealthResponse:
        return RealtimeSourceHealthResponse(
            sourceId=str(item.get("sourceId", "")),
            sourceKind=str(item.get("sourceKind", "")),
            label=str(item.get("label", ""))[:120],
            state=str(item.get("state", "unknown")),
            stage=str(item.get("stage")) if item.get("stage") is not None else None,
            level=float(item.get("level", 0) or 0),
            lastSignalAtMs=int(item["lastSignalAtMs"]) if item.get("lastSignalAtMs") is not None else None,
            frameCount=int(item["frameCount"]) if item.get("frameCount") is not None else None,
            lastFrameAtMs=int(item["lastFrameAtMs"]) if item.get("lastFrameAtMs") is not None else None,
            backendFrameCount=int(item["backendFrameCount"]) if item.get("backendFrameCount") is not None else None,
            lastBackendFrameAtMs=int(item["lastBackendFrameAtMs"]) if item.get("lastBackendFrameAtMs") is not None else None,
            pendingFrameCount=int(item["pendingFrameCount"]) if item.get("pendingFrameCount") is not None else None,
            oldestPendingFrameAgeMs=int(item["oldestPendingFrameAgeMs"]) if item.get("oldestPendingFrameAgeMs") is not None else None,
            droppedFrameCount=int(item["droppedFrameCount"]) if item.get("droppedFrameCount") is not None else None,
            reconnectCount=int(item["reconnectCount"]) if item.get("reconnectCount") is not None else None,
            lastAckAtMs=int(item["lastAckAtMs"]) if item.get("lastAckAtMs") is not None else None,
            lastReconnectReason=str(item.get("lastReconnectReason")) if item.get("lastReconnectReason") is not None else None,
            noiseFloor=float(item["noiseFloor"]) if item.get("noiseFloor") is not None else None,
            captureProcessor=str(item.get("captureProcessor")) if item.get("captureProcessor") is not None else None,
            errorCode=str(item.get("errorCode")) if item.get("errorCode") is not None else None,
            providerMode=str(item.get("providerMode")) if item.get("providerMode") is not None else None,
            providerConnectionState=str(item.get("providerConnectionState")) if item.get("providerConnectionState") is not None else None,
            providerErrorCode=str(item.get("providerErrorCode")) if item.get("providerErrorCode") is not None else None,
        )

    def _maybe_detect_question(self, *, transcript: TranscriptSegmentRecord) -> QuestionCandidateRecord | None:
        if transcript.source_kind != "system":
            return None
        text, source_segment_ids, confidence = self._assemble_interviewer_question_turn(transcript=transcript)
        if not self._looks_like_question(text):
            return None
        source_segment_id_set = set(source_segment_ids)
        existing_turn_candidate = next((
            candidate
            for candidate in reversed(self.repository.list_candidates_for_session(session_id=transcript.session_id))
            if source_segment_id_set.intersection(candidate.source_segment_ids)
        ), None)
        if existing_turn_candidate is not None:
            if (
                existing_turn_candidate.text != text
                or existing_turn_candidate.source_segment_ids != source_segment_ids
                or existing_turn_candidate.confidence != confidence
            ):
                return self.repository.save_candidate(replace(
                    existing_turn_candidate,
                    text=text,
                    source_segment_ids=source_segment_ids,
                    confidence=confidence,
                    updated_at_ms=_now_ms(),
                ))
            return existing_turn_candidate
        candidate_id = f"question:{transcript.session_id}:{transcript.segment_id}"
        existing = self.repository.get_candidate(candidate_id)
        if existing is not None:
            return existing
        if confidence < self.settings.realtime_question_auto_confirm_threshold:
            return self.repository.save_candidate(
                QuestionCandidateRecord(
                    candidate_id=candidate_id,
                    session_id=transcript.session_id,
                    owner_user_id=transcript.owner_user_id,
                    source_segment_ids=source_segment_ids,
                    text=text,
                    state="needs-confirmation",
                    reason="low-transcript-confidence",
                    confidence=confidence,
                    created_at_ms=_now_ms(),
                    updated_at_ms=_now_ms(),
                )
            )
        return self.repository.save_candidate(
            QuestionCandidateRecord(
                candidate_id=candidate_id,
                session_id=transcript.session_id,
                owner_user_id=transcript.owner_user_id,
                source_segment_ids=source_segment_ids,
                text=text,
                state="confirmed",
                reason="auto-confirmed",
                confidence=confidence,
                created_at_ms=_now_ms(),
                updated_at_ms=_now_ms(),
            )
        )

    def _assemble_interviewer_question_turn(
        self,
        *,
        transcript: TranscriptSegmentRecord,
    ) -> tuple[str, list[str], float]:
        if transcript.source_kind != "system" or not transcript.is_final or transcript.overlap:
            return transcript.text.strip(), [transcript.segment_id], transcript.transcript_confidence
        records = self.repository.list_transcripts_for_session(session_id=transcript.session_id)
        candidate_boundary = max((
            item.ended_at_ms
            for item in records
            if item.source_kind == "microphone" and item.is_final and item.ended_at_ms <= transcript.started_at_ms
        ), default=-1)
        eligible = [
            item for item in records
            if item.source_kind == "system"
            and item.is_final
            and not item.overlap
            and item.ended_at_ms > candidate_boundary
            and item.ended_at_ms <= transcript.ended_at_ms
        ]
        if not any(item.segment_id == transcript.segment_id for item in eligible):
            eligible.append(transcript)
        eligible.sort(key=lambda item: (item.started_at_ms, item.ended_at_ms, item.segment_id))
        selected = [transcript]
        for previous in reversed([item for item in eligible if item.segment_id != transcript.segment_id]):
            first = selected[0]
            gap_ms = first.started_at_ms - previous.ended_at_ms
            if gap_ms < -250 or gap_ms > 1_200:
                break
            if transcript.ended_at_ms - previous.started_at_ms > 45_000 or len(selected) >= 4:
                break
            selected.insert(0, previous)
        texts: list[str] = []
        source_segment_ids: list[str] = []
        for item in selected:
            current = " ".join(item.text.split()).strip()
            if not current:
                continue
            compact_current = self._compact_transcript_for_dedup(current)
            if texts:
                compact_previous = self._compact_transcript_for_dedup(texts[-1])
                if compact_previous == compact_current or compact_previous in compact_current or compact_current in compact_previous:
                    if len(compact_current) >= len(compact_previous):
                        texts[-1] = current
                    source_segment_ids.append(item.segment_id)
                    continue
            texts.append(current)
            source_segment_ids.append(item.segment_id)
        return " ".join(texts).strip(), source_segment_ids or [transcript.segment_id], min(item.transcript_confidence for item in selected)

    @staticmethod
    def _looks_like_question(text: str) -> bool:
        lowered = text.strip().lower()
        return lowered.endswith(("?", "？")) or bool(re.match(
            r"^(?:请|麻烦|能否|可以|可不可以)?(?:你|您)?(?:介绍|说明|讲|谈|分析|设计|实现|比较|解释)",
            lowered,
        )) or any(
            key in lowered
            for key in ["讲讲", "怎么", "如何", "为什么", "能不能", "是否", "有没有", "哪一个", "哪些", "多少", "多久", "describe", "tell me", "what", "how", "why"]
        )

    def _require_publisher_token(self, token: str) -> RealtimePublisherRecord:
        publisher = self.repository.get_publisher_by_token(token)
        if publisher is None:
            raise DomainRequestError("realtime-speech", "publisher-token", "实时语音发布令牌无效。", 404)
        if publisher.status in {"closed", "failed"}:
            raise DomainRequestError("realtime-speech", "publisher-token", "该发布通道已被新的面试会话替换。", 410)
        return publisher

    def _require_candidate(self, *, user_id: str, candidate_id: str) -> QuestionCandidateRecord:
        candidate = self.repository.get_candidate(candidate_id)
        if candidate is None:
            raise DomainRequestError("realtime-speech", "candidate", "问题候选不存在。", 404)
        if candidate.owner_user_id != user_id:
            raise DomainRequestError("realtime-speech", "candidate", "不能操作其他用户的问题候选。", 403)
        return candidate

    def _save_event(self, *, session_id: str, owner_user_id: str, kind, payload: dict[str, object]) -> RealtimeEvent:
        event_id = f"rt-event-{uuid4().hex}"
        created_at_ms = _now_ms()
        performance = payload.get("performance")
        if isinstance(performance, dict):
            performance = {**performance, "eventId": event_id, "redisEventXaddAtMs": created_at_ms}
            payload = {**payload, "performance": performance}
            trace_id = performance.get("traceId")
            self._observe_trace(
                str(trace_id) if trace_id else None,
                eventId=event_id,
                redisEventXaddAtMs=created_at_ms,
            )
        stored = self.repository.save_event(
            RealtimeEvent(
                event_id=event_id,
                session_id=session_id,
                owner_user_id=owner_user_id,
                kind=kind,
                payload=payload,
                created_at_ms=created_at_ms,
            )
        )
        stored_performance = stored.payload.get("performance")
        if isinstance(stored_performance, dict):
            stored_trace_id = stored_performance.get("traceId")
            self._observe_trace(
                str(stored_trace_id) if stored_trace_id else None,
                **stored_performance,
            )
        return stored

    def publish_session_event(
        self,
        *,
        user_id: str,
        session_id: str,
        kind,
        payload: dict[str, object],
    ) -> RealtimeEvent:
        """Publish a safe cross-module event into the session's canonical stream."""
        self.session_service.get_session(user_id=user_id, session_id=session_id)
        return self._save_event(
            session_id=session_id,
            owner_user_id=user_id,
            kind=kind,
            payload=payload,
        )

    def list_session_events_after(
        self,
        *,
        user_id: str,
        session_id: str,
        cursor: int,
    ) -> tuple[int, list[RealtimeEvent], bool]:
        current_cursor, events, resumable = self.repository.list_events_after(
            session_id=session_id,
            cursor=cursor,
        )
        return current_cursor, [event for event in events if event.owner_user_id == user_id], resumable

    def wait_for_session_events_after(
        self,
        *,
        user_id: str,
        session_id: str,
        cursor: int,
        timeout_ms: int,
    ) -> tuple[int, list[RealtimeEvent], bool]:
        current_cursor, events, resumable = self.repository.wait_for_events_after(
            session_id=session_id,
            cursor=cursor,
            timeout_ms=timeout_ms,
        )
        return current_cursor, [event for event in events if event.owner_user_id == user_id], resumable

    def acknowledge_runtime_timing(
        self,
        *,
        user_id: str,
        session_id: str,
        trace_id: str,
        stage: str,
        duration_ms: int,
        task_id: str | None = None,
        event_id: str | None = None,
        browser_event_receive_at_ms: int | None = None,
        browser_state_update_at_ms: int | None = None,
        browser_render_at_ms: int | None = None,
        visibility_state: str | None = None,
        browser_stream_chunk_received_at_ms: int | None = None,
        browser_event_parsed_at_ms: int | None = None,
        transcript_store_update_start_at_ms: int | None = None,
        transcript_store_update_complete_at_ms: int | None = None,
        react_render_start_at_ms: int | None = None,
        react_commit_at_ms: int | None = None,
        browser_paint_at_ms: int | None = None,
        rendered_revision: int | None = None,
        rendered_text_length: int | None = None,
    ) -> RealtimeEvent:
        self.session_service.get_session(user_id=user_id, session_id=session_id)
        if stage in {"transcript-delivery", "transcript-render"}:
            for source_kind in ("microphone", "system"):
                timing = self._latest_timing(session_id=session_id, source_kind=source_kind)  # type: ignore[arg-type]
                if timing is not None and timing.get("traceId") == trace_id:
                    self._set_latest_timing(
                        session_id=session_id,
                        source_kind=source_kind,  # type: ignore[arg-type]
                        timing={**timing, "frontendRenderMs": duration_ms},
                    )
            browser_fields = {
                "eventId": event_id,
                "browserEventReceiveAtMs": browser_event_receive_at_ms,
                "browserStateUpdateAtMs": browser_state_update_at_ms,
                "browserRenderAtMs": browser_render_at_ms,
                "visibilityState": visibility_state,
                "browserStreamChunkReceivedAtMs": browser_stream_chunk_received_at_ms,
                "browserEventParsedAtMs": browser_event_parsed_at_ms,
                "transcriptStoreUpdateStartAtMs": transcript_store_update_start_at_ms,
                "transcriptStoreUpdateCompleteAtMs": transcript_store_update_complete_at_ms,
                "reactRenderStartAtMs": react_render_start_at_ms,
                "reactCommitAtMs": react_commit_at_ms,
                "browserPaintAtMs": browser_paint_at_ms,
                "renderedRevision": rendered_revision,
                "renderedTextLength": rendered_text_length,
            }
            self._observe_trace(trace_id, **{
                key: value for key, value in browser_fields.items() if value is not None
            })
        log_event(
            self.logger,
            logging.INFO,
            settings=self.settings,
            event="runtime.performance_acknowledged",
            feature="runtime-performance",
            action=stage,
            session_id=session_id,
            task_id=task_id,
            duration_ms=duration_ms,
        )
        return RealtimeEvent(
            event_id=f"metric:{trace_id}:{stage}",
            session_id=session_id,
            owner_user_id=user_id,
            kind="performance-ack",
            payload={"traceId": trace_id, "stage": stage, "durationMs": duration_ms},
            created_at_ms=_now_ms(),
        )

    @staticmethod
    def _event_payload(event: RealtimeEvent) -> dict[str, object]:
        return {"kind": event.kind, "payload": event.payload, "eventId": event.event_id, "createdAtMs": event.created_at_ms}

    @staticmethod
    def desktop_binding_response(record: SessionDesktopBindingRecord) -> DesktopDeviceBindingResponse:
        return DesktopDeviceBindingResponse(
            bindingId=record.binding_id,
            sessionId=record.session_id,
            ownerUserId=record.owner_user_id,
            deviceId=record.device_id,
            manualCode=record.manual_code,
            displayName=record.display_name,
            capabilities=record.capabilities,
            status=record.status,
            boundAtMs=record.bound_at_ms,
            lastSeenAtMs=record.last_seen_at_ms,
            bindingGeneration=record.binding_generation,
            permissionStatus={
                "microphone": record.capabilities.get("microphone", "unknown"),
                "systemAudio": record.capabilities.get("systemAudio", "unknown"),
                "screenCapture": record.capabilities.get("screenCapture", "unknown"),
            },
            devicePresence="online",
            accountBound=True,
            sessionConnection="connected" if record.status == "bound" else "disconnected",
        )

    @staticmethod
    def _publisher_response(record: RealtimePublisherRecord) -> RealtimePublisherResponse:
        return RealtimePublisherResponse(
            publisherId=record.publisher_id,
            token=record.token,
            sessionId=record.session_id,
            ownerUserId=record.owner_user_id,
            sourceKind=record.source_kind,
            clientName=record.client_name,
            issuedAtMs=record.issued_at_ms,
            expiresAtMs=record.expires_at_ms,
            connectedAtMs=record.connected_at_ms,
            disconnectedAtMs=record.disconnected_at_ms,
            status=record.status,
        )

    @staticmethod
    def _transcript_response(record: TranscriptSegmentRecord) -> TranscriptSegmentResponse:
        return TranscriptSegmentResponse(
            segmentId=record.segment_id,
            sourceId=record.source_id,
            sourceKind=record.source_kind,
            role=record.role,
            revision=record.revision,
            text=record.text,
            transcriptConfidence=record.transcript_confidence,
            startedAtMs=record.started_at_ms,
            endedAtMs=record.ended_at_ms,
            isFinal=record.is_final,
            terminalState=record.terminal_state,
            finalizationReason=record.finalization_reason,
            overlap=record.overlap,
            createdAtMs=record.created_at_ms,
            publishedAtMs=record.published_at_ms,
            performance=(RealtimeStageTimingResponse(**record.performance) if record.performance is not None else None),
        )

    @staticmethod
    def _candidate_response(record: QuestionCandidateRecord) -> QuestionCandidateResponse:
        return QuestionCandidateResponse(
            candidateId=record.candidate_id,
            sourceSegmentIds=record.source_segment_ids,
            text=record.text,
            state=record.state,
            reason=record.reason,
            confidence=record.confidence,
            answerTaskId=record.answer_task_id,
            createdAtMs=record.created_at_ms,
            updatedAtMs=record.updated_at_ms,
        )

    def _log(self, level: int, event: str, *, session_id: str, publisher_id: str | None, state: str, error_code: str | None = None) -> None:
        log_event(
            self.logger,
            level,
            settings=self.settings,
            event=event,
            feature="realtime-speech",
            action="realtime-audio",
            session_id=session_id,
            publisher_id=publisher_id,
            state=state,
            error_code=error_code,
        )
