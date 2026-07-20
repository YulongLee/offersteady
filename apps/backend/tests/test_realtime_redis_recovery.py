from __future__ import annotations

import os
from uuid import uuid4

import pytest
from redis import Redis

from app.core.config import Settings
from app.ports.realtime_speech import DesktopDeviceRecord, RealtimeEvent
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
