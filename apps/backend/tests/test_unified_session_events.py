from __future__ import annotations

import threading
import time

from app.ports.realtime_speech import RealtimeEvent
from app.services.realtime_speech_repository import InMemoryRealtimeSpeechRepository


def _event(event_id: str, created_at_ms: int) -> RealtimeEvent:
    return RealtimeEvent(
        event_id=event_id,
        session_id="session-unified-events",
        owner_user_id="synthetic-user",
        kind="screenshot-capture-updated",
        payload={"requestId": event_id, "status": "requested"},
        created_at_ms=created_at_ms,
    )


def test_incremental_session_events_follow_cursor_order_and_resume() -> None:
    repository = InMemoryRealtimeSpeechRepository()
    first = repository.save_event(_event("event-1", 20))
    second = repository.save_event(_event("event-2", 10))

    cursor, events, resumable = repository.list_events_after(session_id=first.session_id, cursor=0)
    assert cursor == 2
    assert resumable is True
    assert [event.event_id for event in events] == ["event-1", "event-2"]

    next_cursor, remaining, resumable = repository.list_events_after(session_id=second.session_id, cursor=1)
    assert next_cursor == 2
    assert resumable is True
    assert [event.event_id for event in remaining] == ["event-2"]


def test_session_event_payload_does_not_require_binary_content() -> None:
    repository = InMemoryRealtimeSpeechRepository()
    repository.save_event(_event("request-safe", 1))
    _cursor, events, _resumable = repository.list_events_after(session_id="session-unified-events", cursor=0)

    assert events[0].payload == {"requestId": "request-safe", "status": "requested"}
    assert "audio" not in events[0].payload
    assert "screenshot" not in events[0].payload


def test_wait_for_session_events_wakes_when_event_is_saved() -> None:
    repository = InMemoryRealtimeSpeechRepository()

    def publish() -> None:
        time.sleep(0.03)
        repository.save_event(_event("event-wakeup", 30))

    worker = threading.Thread(target=publish)
    worker.start()
    started = time.perf_counter()
    cursor, events, resumable = repository.wait_for_events_after(
        session_id="session-unified-events",
        cursor=0,
        timeout_ms=500,
    )
    elapsed_ms = (time.perf_counter() - started) * 1000
    worker.join()

    assert elapsed_ms < 300
    assert cursor == 1
    assert resumable is True
    assert [event.event_id for event in events] == ["event-wakeup"]


def test_wait_for_session_events_returns_after_bounded_timeout() -> None:
    repository = InMemoryRealtimeSpeechRepository()
    started = time.perf_counter()
    cursor, events, resumable = repository.wait_for_events_after(
        session_id="session-unified-events",
        cursor=0,
        timeout_ms=30,
    )
    elapsed_ms = (time.perf_counter() - started) * 1000

    assert 20 <= elapsed_ms < 250
    assert cursor == 0
    assert events == []
    assert resumable is True
