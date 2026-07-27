from __future__ import annotations

import os
from dataclasses import replace
from uuid import uuid4

import pytest
from redis import Redis

from app.core.config import Settings
from app.ports.realtime_speech import DesktopDeviceRecord, RealtimeEvent, TranscriptSegmentRecord
from app.services.redis_realtime_speech_repository import RedisRealtimeSpeechRepository


REDIS_URL = os.environ.get("OFFERSTEADY_TEST_REDIS_URL")
pytestmark = pytest.mark.skipif(not REDIS_URL, reason="OFFERSTEADY_TEST_REDIS_URL is required")


def test_runtime_recovers_across_repository_instances_and_stream_cursor_advances():
    assert REDIS_URL
    client = Redis.from_url(REDIS_URL, decode_responses=True)
    client.flushdb()
    settings = Settings(redis_url=REDIS_URL, realtime_runtime_ttl_seconds=300)
    first = RedisRealtimeSpeechRepository(settings)
    suffix = uuid4().hex[:8]
    device = DesktopDeviceRecord(
        device_id=f"device-{suffix}",
        manual_code="654321",
        display_name="Synthetic restart device",
        capabilities={"protocolVersion": "2.0"},
        registered_at_ms=1,
        last_seen_at_ms=2,
    )
    first.save_desktop_device(device)
    first.save_event(RealtimeEvent(
        event_id=f"event-{suffix}",
        session_id=f"session-{suffix}",
        owner_user_id="synthetic-user",
        kind="connection-state",
        payload={"status": "connected"},
        created_at_ms=3,
    ))

    restarted = RedisRealtimeSpeechRepository(settings)
    assert restarted.get_desktop_device_by_code("654321") == device
    assert restarted.get_event_stream_version(session_id=f"session-{suffix}") == 1
    assert client.ttl("offersteady:realtime:runtime:v2") > 0
    assert client.ttl(f"offersteady:realtime:events:session-{suffix}") > 0


def test_transcript_revision_advances_stream_cursor_without_realtime_event():
    assert REDIS_URL
    client = Redis.from_url(REDIS_URL, decode_responses=True)
    client.flushdb()
    settings = Settings(redis_url=REDIS_URL, realtime_runtime_ttl_seconds=300)
    repository = RedisRealtimeSpeechRepository(settings)
    suffix = uuid4().hex[:8]
    session_id = f"session-transcript-{suffix}"
    segment = TranscriptSegmentRecord(
        segment_id=f"segment-{suffix}",
        session_id=session_id,
        owner_user_id="synthetic-user",
        source_id="microphone",
        source_kind="microphone",
        role="candidate",
        revision=1,
        text="第一条实时字幕",
        transcript_confidence=0.96,
        started_at_ms=1,
        ended_at_ms=2,
        is_final=False,
        overlap=False,
        created_at_ms=2,
        published_at_ms=3,
    )

    repository.save_transcript(segment)
    first_cursor = repository.get_event_stream_version(session_id=session_id)
    repository.save_transcript(replace(segment, revision=2, text="第二条实时字幕", published_at_ms=4))
    second_cursor = repository.get_event_stream_version(session_id=session_id)
    restarted = RedisRealtimeSpeechRepository(settings)

    assert first_cursor == 1
    assert second_cursor == 2
    assert restarted.get_event_stream_version(session_id=session_id) == 2
    assert client.ttl("offersteady:realtime:runtime:v2:activity") > 0
