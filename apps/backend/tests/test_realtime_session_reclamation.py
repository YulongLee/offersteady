from __future__ import annotations

import queue
from collections import deque
import logging
import threading
from types import SimpleNamespace

from app.core.config import Settings
from app.deps import realtime_speech_service
from app.ports.realtime_speech import (
    RealtimeEvent,
    RealtimeFrameReceiptRecord,
    RealtimePublisherRecord,
    TranscriptSegmentRecord,
)
from app.services.realtime_speech_repository import InMemoryRealtimeSpeechRepository
from app.services.realtime_speech_service import RealtimeSpeechService
from app.services.redis_realtime_speech_repository import RedisRealtimeSpeechRepository


def _minimal_reclamation_service() -> RealtimeSpeechService:
    service = object.__new__(RealtimeSpeechService)
    service.logger = logging.getLogger("realtime-reclamation-regression")
    service._session_activity_lock = threading.Lock()
    service._session_cleanup_locks = {}
    service._session_cleanup_lock_users = {}
    service._frame_worker_lock = threading.Lock()
    service._retired_session_ids = set()
    service._retired_session_order = deque(maxlen=2)
    return service


def test_session_reset_is_idempotent_and_releases_ephemeral_state() -> None:
    service = realtime_speech_service()
    session_id = "reclamation-regression-session"
    source_kind = "microphone"
    source_key = (session_id, source_kind)
    segment_key = (session_id, source_kind, "segment-1")
    work_queue: queue.Queue[dict[str, object]] = queue.Queue()
    work_queue.put({"frame": "stale"})

    with service._frame_worker_lock:
        service._frame_queues[source_key] = work_queue
        service._frame_workers[source_key] = None  # type: ignore[assignment]
        service._active_requests_by_session_source[source_key] = 1
        service._latest_timings_by_session_source[source_key] = {"status": "processing"}
        service._queue_wait_samples[source_key] = deque([10])
        service._counters_by_session_source[source_key] = {"queueDepth": 1}
    with service._segment_audio_lock:
        service._segment_audio_buffers[segment_key] = {"audioBytes": 128}
    with service._watchdog_lock:
        service._active_source_turns[source_key] = {"turnId": "turn-1"}
    service.repository.save_frame_receipt(RealtimeFrameReceiptRecord(
        session_id=session_id,
        owner_user_id="reclamation-owner",
        publisher_id="reclamation-publisher",
        device_id="reclamation-device",
        source_id="microphone",
        source_kind=source_kind,
        sequence=1,
        frame_count=1,
        captured_at_ms=1,
        received_at_ms=1,
    ))

    first = service._reset_realtime_session(session_id=session_id, retired=True)
    second = service._reset_realtime_session(session_id=session_id, retired=True)

    assert first["cleared_queues"] == 1
    assert first["cleared_buffered_segments"] == 1
    assert second["cleared_queues"] == 0
    assert second["cleared_buffered_segments"] == 0
    assert source_key not in service._frame_queues
    assert source_key not in service._active_source_turns
    assert segment_key not in service._segment_audio_buffers
    assert service.repository.list_frame_receipts_for_session(session_id=session_id) == []
    assert first["cleared_frame_receipts"] == 1
    assert second["cleared_frame_receipts"] == 0


def test_reclamation_metrics_are_safe_and_expose_resource_counts() -> None:
    service = realtime_speech_service()
    before = service.reclamation_metrics()

    service._record_reclamation(
        reason="test",
        session_id="reclamation-metrics-session",
        duration_ms=7,
        resources={
            "releasedBindings": 1,
            "closedPublishers": 2,
            "closedAsrSessions": 1,
            "clearedQueues": 1,
            "clearedBufferedSegments": 3,
            "clearedFrameReceipts": 4,
        },
    )

    after = service.reclamation_metrics()
    assert after["candidates"] == before["candidates"] + 1
    assert after["reclaimed"] == before["reclaimed"] + 1
    assert after["lastReason"] == "test"
    assert after["lastDurationMs"] == 7
    assert after["releasedBindings"] == before["releasedBindings"] + 1
    assert after["clearedBufferedSegments"] == before["clearedBufferedSegments"] + 3
    assert after["clearedFrameReceipts"] == before["clearedFrameReceipts"] + 4


def test_ended_session_runtime_cleanup_preserves_review_transcripts() -> None:
    repository = InMemoryRealtimeSpeechRepository()
    session_id = "runtime-cleanup-session"
    repository.save_event(RealtimeEvent(
        event_id="runtime-event",
        session_id=session_id,
        owner_user_id="runtime-owner",
        kind="connection-state",
        payload={"status": "connected"},
        created_at_ms=1,
    ))
    repository.save_transcript(TranscriptSegmentRecord(
        segment_id="runtime-segment",
        session_id=session_id,
        owner_user_id="runtime-owner",
        source_id="microphone",
        source_kind="microphone",
        role="candidate",
        revision=1,
        text="review transcript",
        transcript_confidence=0.9,
        started_at_ms=1,
        ended_at_ms=2,
        is_final=True,
        overlap=False,
        created_at_ms=2,
    ))
    repository.save_publisher(RealtimePublisherRecord(
        publisher_id="runtime-publisher",
        token="runtime-token",
        session_id=session_id,
        owner_user_id="runtime-owner",
        source_kind="microphone",
        client_name="test",
        issued_at_ms=1,
        expires_at_ms=10_000,
    ))

    first = repository.clear_session_runtime(session_id=session_id)
    second = repository.clear_session_runtime(session_id=session_id)

    assert first["cleared_events"] == 1
    assert first["cleared_publishers"] == 1
    assert repository.list_events_for_session(session_id=session_id) == []
    assert repository.list_transcripts_for_session(session_id=session_id)[0].text == "review transcript"
    assert second["cleared_events"] == 0
    assert second["cleared_publishers"] == 0


def test_cleanup_lock_identity_is_kept_until_the_last_caller_releases_it() -> None:
    service = _minimal_reclamation_service()

    first = service._acquire_session_cleanup_lock("session-1")
    second = service._acquire_session_cleanup_lock("session-1")

    assert first is second
    service._release_session_cleanup_lock("session-1", first)
    assert service._session_cleanup_locks["session-1"] is first
    service._release_session_cleanup_lock("session-1", second)
    assert "session-1" not in service._session_cleanup_locks
    assert "session-1" not in service._session_cleanup_lock_users


def test_retired_session_fence_is_bounded_and_blocks_late_event_writes() -> None:
    service = _minimal_reclamation_service()
    service.repository = InMemoryRealtimeSpeechRepository()

    service._retire_session_id("session-1")
    service._retire_session_id("session-2")
    service._retire_session_id("session-3")
    event = service._save_event(
        session_id="session-3",
        owner_user_id="owner-3",
        kind="connection-state",
        payload={"status": "late"},
    )

    assert service._retired_session_ids == {"session-2", "session-3"}
    assert list(service._retired_session_order) == ["session-2", "session-3"]
    assert event.payload == {"status": "late"}
    assert service.repository.list_events_for_session(session_id="session-3") == []


def test_orphan_sweep_reclaims_only_runtime_for_ended_sessions() -> None:
    service = _minimal_reclamation_service()
    service.settings = Settings(
        _env_file=None,
        interview_idle_reaper_batch_size=8,
        realtime_session_reclamation_dry_run=False,
    )
    service.repository = SimpleNamespace(
        list_runtime_session_owners=lambda *, limit: {
            "ended-session": "owner-1",
            "live-session": "owner-2",
        }
    )
    service.session_service = SimpleNamespace(
        get_session=lambda *, user_id, session_id: SimpleNamespace(
            session_id=session_id,
            owner_user_id=user_id,
            status="ended" if session_id == "ended-session" else "live",
        )
    )
    reclaimed: list[tuple[str, str]] = []
    service.terminate_session_for_admin = lambda **kwargs: reclaimed.append(
        (str(kwargs["session_id"]), str(kwargs["reason"]))
    )

    assert service._sweep_ended_runtime_orphans() == 1
    assert reclaimed == [("ended-session", "ended-runtime-orphan")]


def test_redis_orphan_candidate_scan_rotates_across_runtime_indexes() -> None:
    repository = object.__new__(RedisRealtimeSpeechRepository)
    repository._publisher_key = "publishers"
    repository._receipt_key = "receipts"
    repository._web_heartbeat_entity_key = "heartbeats"
    repository._runtime_owner_scan_lock = threading.Lock()
    repository._runtime_owner_scan_cursors = {}
    repository._runtime_owner_scan_key_index = 0
    records = {
        "publishers": {"p1": '{"session_id":"session-p","owner_user_id":"owner-p"}'},
        "receipts": {"r1": '{"session_id":"session-r","owner_user_id":"owner-r"}'},
        "heartbeats": {"h1": '{"session_id":"session-h","owner_user_id":"owner-h"}'},
    }
    repository._redis = SimpleNamespace(
        hscan=lambda key, *, cursor, count: (0, records[key]),
    )

    scans = [repository.list_runtime_session_owners(limit=1) for _ in range(3)]

    assert scans == [
        {"session-p": "owner-p"},
        {"session-r": "owner-r"},
        {"session-h": "owner-h"},
    ]
