from __future__ import annotations

import queue
from collections import deque

from app.deps import realtime_speech_service
from app.ports.realtime_speech import RealtimeFrameReceiptRecord


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
