from __future__ import annotations

import logging
import threading
from dataclasses import replace
from types import SimpleNamespace

import pytest

from app.core.config import Settings
from app.ports.realtime_speech import (
    AudioFrame, RealtimeFrameReceiptRecord, RealtimePublisherRecord, TranscriptResult, TranscriptSegmentRecord,
)
from app.services.realtime_speech_repository import InMemoryRealtimeSpeechRepository
from app.services.realtime_speech_service import RealtimeSpeechService


def service_with_synthetic_state():
    return RealtimeSpeechService(
        settings=Settings(_env_file=None), logger=logging.getLogger("synthetic-cleanup-race"),
        repository=InMemoryRealtimeSpeechRepository(), session_service=SimpleNamespace(),
        asr_gateway=SimpleNamespace(close_all_sessions=lambda: 0),
    )


def synthetic_final():
    return TranscriptSegmentRecord(
        segment_id="synthetic-segment", session_id="synthetic-session", owner_user_id="synthetic-owner",
        source_id="synthetic-system", source_kind="system", role="interviewer", revision=3,
        text="请介绍合成项目中缓存设计的取舍", transcript_confidence=0.96,
        started_at_ms=100, ended_at_ms=200, is_final=True, overlap=False, created_at_ms=200,
    )


def thread_call(operation):
    errors = []

    def invoke():
        try:
            operation()
        except BaseException as exc:
            errors.append(exc)

    thread = threading.Thread(target=invoke)
    thread.start()
    return thread, errors


def test_cleanup_after_initial_retired_check_cannot_recreate_stable_state():
    service = service_with_synthetic_state()
    transcript = synthetic_final()
    initial_checked, resume = threading.Event(), threading.Event()
    original = service._session_is_retired
    calls = []

    def gated_check(session_id):
        result = original(session_id)
        if threading.current_thread() is observer[0] and not initial_checked.is_set():
            initial_checked.set()
            assert resume.wait(2)
        return result

    observer = [None]
    # Capture identity before starting, so the first check is deterministically
    # gated rather than relying on thread scheduling.
    def observe():
        observer[0] = threading.current_thread()
        service._observe_stable_interviewer_partial(transcript)

    service._session_is_retired = gated_check
    service._question_prefetch_scheduler = SimpleNamespace(
        submit=lambda **kwargs: calls.append(kwargs), clear_session=lambda **_kwargs: None, shutdown=lambda: None,
    )
    thread, errors = thread_call(observe)
    try:
        assert initial_checked.wait(1)
        service._retire_session_id(transcript.session_id)
        service._clear_session_state_indexes(session_id=transcript.session_id)
        resume.set()
        thread.join(2)
        assert not thread.is_alive() and errors == []
        assert service._stable_question_state == {}
        assert service._stable_question_generations == {}
        assert service.repository.list_events_for_session(session_id=transcript.session_id) == []
        assert calls == []
    finally:
        resume.set()
        thread.join(2)
        service.shutdown()


def test_cleanup_and_final_admission_are_one_memory_transaction():
    service = service_with_synthetic_state()
    transcript = synthetic_final()
    event_saved, checked, resume, cleanup_done = (threading.Event() for _ in range(4))
    original = service._session_is_retired
    observer = [None]
    operations = []
    active = []

    def save_event(**_kwargs):
        assert not service._stable_question_state_lock.locked()
        event_saved.set()
        return SimpleNamespace()

    def gated_check(session_id):
        result = original(session_id)
        if (threading.current_thread() is observer[0] and event_saved.is_set()
                and not checked.is_set()):
            checked.set()
            assert resume.wait(2)
        return result

    def submit(**_kwargs):
        operations.append("submit")
        active.append(True)

    def clear(**_kwargs):
        operations.append("clear")
        active.clear()

    service._save_event = save_event
    service._session_is_retired = gated_check
    service._question_prefetch_scheduler = SimpleNamespace(submit=submit, clear_session=clear, shutdown=lambda: None)

    def observe():
        observer[0] = threading.current_thread()
        service._observe_stable_interviewer_partial(transcript)

    def cleanup():
        service._retire_session_id(transcript.session_id)
        service._clear_session_state_indexes(session_id=transcript.session_id)
        cleanup_done.set()

    thread, errors = thread_call(observe)
    cleanup_thread = None
    try:
        assert checked.wait(1)
        cleanup_thread, cleanup_errors = thread_call(cleanup)
        # The old implementation let cleanup return, then admitted stale work.
        # The short shared lock now orders pure admission before cleanup.
        assert not cleanup_done.wait(0.03)
        resume.set()
        thread.join(2)
        cleanup_thread.join(2)
        assert not thread.is_alive() and not cleanup_thread.is_alive()
        assert errors == [] and cleanup_errors == []
        assert operations == ["submit", "clear"]
        assert active == []
        assert service._stable_question_state == {}
        assert service._stable_question_generations == {}
    finally:
        resume.set()
        thread.join(2)
        if cleanup_thread is not None:
            cleanup_thread.join(2)
        service.shutdown()


def test_queued_observation_from_before_nonretired_reset_is_rejected():
    service = service_with_synthetic_state()
    transcript = synthetic_final()
    admitted = []
    service._question_prefetch_scheduler = SimpleNamespace(
        submit=lambda **kwargs: admitted.append(kwargs), clear_session=lambda **_kwargs: None, shutdown=lambda: None,
    )
    try:
        queued_generation = service._stable_question_observation_generation(session_id=transcript.session_id)
        assert queued_generation is not None
        service._clear_session_state_indexes(session_id=transcript.session_id, release_screenshot=False)
        assert not service._session_is_retired(transcript.session_id)
        fresh_generation = service._stable_question_observation_generation(session_id=transcript.session_id)
        assert fresh_generation is not queued_generation
        assert service._observe_stable_interviewer_partial(
            transcript, observation_generation=queued_generation,
        ) is None
        assert service._stable_question_state == {}
        assert admitted == []
        assert service._observe_stable_interviewer_partial(
            transcript, observation_generation=fresh_generation,
        ) is not None
        assert len(admitted) == 1
    finally:
        service.shutdown()


def test_observation_generation_tracking_is_bounded_and_shutdown_revokes_tokens():
    service = service_with_synthetic_state()
    try:
        old = service._stable_question_observation_generation(session_id="synthetic-0")
        for index in range(1, 300):
            service._stable_question_observation_generation(session_id=f"synthetic-{index}")
        assert len(service._stable_question_generations) == 256
        assert old not in service._stable_question_generations.values()
        service.shutdown()
        assert service._stable_question_generations == {}
        assert service._stable_question_observation_generation(session_id="synthetic-new") is None
    finally:
        service.shutdown()


@pytest.mark.parametrize("provider_partial", [True, False])
def test_provider_transcript_io_crossing_nonretired_reset_keeps_old_observation_generation(provider_partial):
    service = service_with_synthetic_state()
    transcript = synthetic_final()
    publishing, resume = threading.Event(), threading.Event()
    admitted, cold_calls = [], []
    publisher = RealtimePublisherRecord(
        publisher_id="synthetic-publisher", token="synthetic-token", session_id=transcript.session_id,
        owner_user_id=transcript.owner_user_id, source_kind="system", client_name="synthetic-test",
        issued_at_ms=1, expires_at_ms=999999,
    )
    service.repository.save_publisher(publisher)
    service.capture_control_state = lambda **_kwargs: "capturing"
    service._session_audio_mode_cache[transcript.session_id] = "computer"
    service._session_language_cache[transcript.session_id] = "zh-CN"
    service._question_prefetch_scheduler = SimpleNamespace(
        submit=lambda **kwargs: admitted.append(kwargs), clear_session=lambda **_kwargs: None, shutdown=lambda: None,
    )
    service._submit_cold = lambda operation, *args, **kwargs: cold_calls.append((operation, args, kwargs))
    original_save_event = service.repository.save_event

    def blocked_transcript_io(event):
        if event.kind == "transcript-updated":
            publishing.set()
            assert resume.wait(2)
        return original_save_event(event)

    service.repository.save_event = blocked_transcript_io
    frame = AudioFrame(
        publisher_id=publisher.publisher_id, session_id=publisher.session_id, device_id="synthetic-device",
        source_id=transcript.source_id, source_kind="system", segment_id=transcript.segment_id,
        revision=transcript.revision, sequence=1, captured_at_ms=100, started_at_ms=100,
        ended_at_ms=200, duration_ms=100, codec="pcm-s16le", sample_rate_hz=16000,
        channels=1, is_final=not provider_partial, audio_bytes=b"synthetic audio",
    )
    result = TranscriptResult(text=transcript.text, confidence=0.96, provider_revision=3)
    if provider_partial:
        operation = lambda: service._publish_provider_partial(frame, result)
    else:
        final = replace(transcript, terminal_state="incomplete")
        service._transcribe_frame = lambda **_kwargs: (final, result)
        receipt = RealtimeFrameReceiptRecord(
            session_id=publisher.session_id, owner_user_id=publisher.owner_user_id,
            publisher_id=publisher.publisher_id, device_id=frame.device_id, source_id=frame.source_id,
            source_kind="system", sequence=1, frame_count=1, captured_at_ms=100,
            received_at_ms=200, asr_status="pending",
        )
        prepared = {
            "publisher": publisher, "frame": frame, "pending_receipt": receipt,
            "counter_bucket": service._counter_bucket(session_id=publisher.session_id, source_kind="system"),
            "ingest_received_at_ms": 200, "captured_at_ms": 100, "source_kind": "system",
        }
        operation = lambda: service._process_prepared_audio_frame(prepared)
    thread, errors = thread_call(operation)
    try:
        assert publishing.wait(1)
        old_generation = service._stable_question_generations[transcript.session_id]
        service._clear_session_state_indexes(session_id=transcript.session_id, release_screenshot=False)
        fresh_generation = service._stable_question_observation_generation(session_id=transcript.session_id)
        assert fresh_generation is not old_generation
        resume.set()
        thread.join(2)
        assert not thread.is_alive() and errors == []
        observers = [(callback, args, kwargs) for callback, args, kwargs in cold_calls
                     if getattr(callback, "__name__", "") == "_observe_stable_interviewer_partial"]
        if provider_partial:
            assert len(observers) == 1
            callback, args, kwargs = observers[0]
            assert kwargs["observation_generation"] is old_generation
            callback(*args, **kwargs)
        assert service._stable_question_state == {}
        assert service._stable_question_generations[transcript.session_id] is fresh_generation
        assert admitted == []
    finally:
        resume.set()
        thread.join(2)
        service.shutdown()
