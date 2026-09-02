from __future__ import annotations

import os
import json
from dataclasses import asdict, replace
from uuid import uuid4

import pytest
from redis import Redis

from app.core.config import Settings
from app.ports.realtime_speech import (
    DesktopDeviceRecord,
    RealtimeEvent,
    SessionDesktopBindingRecord,
    TranscriptSegmentRecord,
    WebSessionHeartbeatRecord,
)
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
    assert client.ttl("offersteady:realtime:runtime:v2:entities:devices:v1") > 0
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


def test_high_frequency_entity_updates_do_not_rewrite_global_snapshot():
    assert REDIS_URL
    client = Redis.from_url(REDIS_URL, decode_responses=True)
    client.flushdb()
    repository = RedisRealtimeSpeechRepository(
        Settings(redis_url=REDIS_URL, realtime_runtime_ttl_seconds=300)
    )
    device = DesktopDeviceRecord(
        device_id="synthetic-device",
        manual_code="123456",
        display_name="Synthetic device",
        capabilities={"protocolVersion": "2.0"},
        registered_at_ms=1,
        last_seen_at_ms=1,
    )

    for revision in range(1, 11):
        repository.save_desktop_device(replace(device, last_seen_at_ms=revision))
        repository.save_web_session_heartbeat(WebSessionHeartbeatRecord(
            session_id="synthetic-session",
            owner_user_id="synthetic-user",
            page="preparation",
            seen_at_ms=revision,
        ))

    diagnostics = repository.operational_diagnostics()
    assert client.exists("offersteady:realtime:runtime:v2") == 0
    assert diagnostics["globalSnapshotWriteCount"] == 0
    assert diagnostics["entityWriteCount"] == 20


def test_legacy_snapshot_seeds_entity_state_and_exact_indexes():
    assert REDIS_URL
    client = Redis.from_url(REDIS_URL, decode_responses=True)
    client.flushdb()
    device = DesktopDeviceRecord(
        device_id="legacy-device",
        manual_code="234567",
        display_name="Legacy synthetic device",
        capabilities={},
        registered_at_ms=10,
        last_seen_at_ms=20,
    )
    binding = SessionDesktopBindingRecord(
        binding_id="legacy-binding",
        session_id="legacy-session",
        owner_user_id="legacy-user",
        device_id=device.device_id,
        manual_code=device.manual_code,
        display_name=device.display_name,
        capabilities={},
        bound_at_ms=30,
        last_seen_at_ms=30,
    )
    heartbeat = WebSessionHeartbeatRecord(
        session_id=binding.session_id,
        owner_user_id=binding.owner_user_id,
        page="live",
        seen_at_ms=40,
        binding_id=binding.binding_id,
        page_instance_id="legacy-page",
        lease_generation=1,
        lease_expires_at_ms=1000,
    )
    client.set("offersteady:realtime:runtime:v2", json.dumps({
        "devices": [asdict(device)],
        "bindings": [asdict(binding)],
        "heartbeats": [asdict(heartbeat)],
    }))

    repository = RedisRealtimeSpeechRepository(
        Settings(redis_url=REDIS_URL, realtime_runtime_ttl_seconds=300)
    )

    assert repository.get_desktop_device_by_code(device.manual_code) == device
    assert repository.get_latest_session_desktop_binding_by_code(
        manual_code=device.manual_code
    ) == binding
    assert repository.get_active_live_web_session(user_id=binding.owner_user_id) == heartbeat
    assert client.hget(
        "offersteady:realtime:runtime:v2:indexes:device-codes:v1",
        device.manual_code,
    ) == device.device_id
    assert repository.operational_diagnostics()["entitySeedCount"] == 3


def test_newer_entity_state_overlays_legacy_and_rebuilds_missing_index():
    assert REDIS_URL
    client = Redis.from_url(REDIS_URL, decode_responses=True)
    client.flushdb()
    legacy = DesktopDeviceRecord(
        device_id="overlay-device",
        manual_code="345678",
        display_name="Legacy",
        capabilities={},
        registered_at_ms=1,
        last_seen_at_ms=10,
        generation=1,
    )
    current = replace(legacy, display_name="Current", last_seen_at_ms=20, generation=2)
    client.set(
        "offersteady:realtime:runtime:v2",
        json.dumps({"devices": [asdict(legacy)]}),
    )
    client.hset(
        "offersteady:realtime:runtime:v2:entities:devices:v1",
        current.device_id,
        json.dumps(asdict(current)),
    )

    repository = RedisRealtimeSpeechRepository(
        Settings(redis_url=REDIS_URL, realtime_runtime_ttl_seconds=300)
    )

    assert repository.get_desktop_device_by_code(current.manual_code) == current
    assert client.hget(
        "offersteady:realtime:runtime:v2:indexes:device-codes:v1",
        current.manual_code,
    ) == current.device_id


def test_incremental_activity_updates_preserve_other_session_fields():
    assert REDIS_URL
    client = Redis.from_url(REDIS_URL, decode_responses=True)
    client.flushdb()
    repository = RedisRealtimeSpeechRepository(
        Settings(redis_url=REDIS_URL, realtime_runtime_ttl_seconds=300)
    )
    activity_key = "offersteady:realtime:runtime:v2:activity"
    client.hset(activity_key, "unrelated-session", 73)
    segment = TranscriptSegmentRecord(
        segment_id="activity-segment",
        session_id="activity-session",
        owner_user_id="synthetic-user",
        source_id="microphone",
        source_kind="microphone",
        role="candidate",
        revision=1,
        text="synthetic transcript",
        transcript_confidence=0.9,
        started_at_ms=1,
        ended_at_ms=2,
        is_final=False,
        overlap=False,
        created_at_ms=2,
        published_at_ms=3,
    )

    repository.save_transcript(segment)
    repository.save_event(RealtimeEvent(
        event_id="activity-event",
        session_id="activity-session",
        owner_user_id="synthetic-user",
        kind="connection-state",
        payload={"status": "connected"},
        created_at_ms=4,
    ))

    assert client.hget(activity_key, "unrelated-session") == "73"
    assert int(client.hget(activity_key, "activity-session") or 0) == 2
