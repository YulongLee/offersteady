from __future__ import annotations

import asyncio
import json
import threading
import time
from dataclasses import asdict

from types import SimpleNamespace

from app.modules.realtime_speech import (
    coalesce_transcript_revisions,
    session_stream_refresh_plan,
    stream_session_runtime,
)
from app.ports.realtime_speech import RealtimeEvent
from app.schemas.realtime_speech import (
    RealtimeEventListResponse,
    RealtimeEventResponse,
    RealtimeQuestionCandidateListResponse,
    RealtimeTranscriptListResponse,
)
from app.services.realtime_event_wait import RealtimeEventWaitExecutor
from app.services.redis_realtime_speech_repository import RedisRealtimeSpeechRepository


def _stream_tuple(value: str) -> tuple[int, int]:
    major, minor = value.split("-", 1)
    return int(major), int(minor)


class SyntheticRedisPipeline:
    def __init__(self, redis: "SyntheticRedis") -> None:
        self.redis = redis

    def zadd(self, *args, **kwargs):
        self.redis.zadd(*args, **kwargs)
        return self

    def hset(self, *args, **kwargs):
        self.redis.hset(*args, **kwargs)
        return self

    def zremrangebyrank(self, *args, **kwargs):
        self.redis.zremrangebyrank(*args, **kwargs)
        return self

    def expire(self, *args, **kwargs):
        self.redis.expire(*args, **kwargs)
        return self

    def execute(self):
        return []


class SyntheticRedis:
    def __init__(self) -> None:
        self.streams: dict[str, list[tuple[str, dict[str, str]]]] = {}
        self.zsets: dict[str, dict[str, float]] = {}
        self.activity: dict[str, int] = {}
        self.hashes: dict[str, dict[str, str]] = {}
        self.full_xrange_calls = 0
        self.bounded_xrange_calls = 0
        self.xread_calls = 0
        self.on_xread = None

    def pipeline(self):
        return SyntheticRedisPipeline(self)

    def expire(self, *_args, **_kwargs):
        return True

    def zadd(self, key, mapping):
        self.zsets.setdefault(key, {}).update({str(member): float(score) for member, score in mapping.items()})
        return len(mapping)

    def zremrangebyrank(self, key, start, stop):
        ordered = sorted(self.zsets.get(key, {}), key=lambda item: (self.zsets[key][item], _stream_tuple(item)))
        length = len(ordered)
        normalized_start = start if start >= 0 else length + start
        normalized_stop = stop if stop >= 0 else length + stop
        normalized_start = max(0, normalized_start)
        normalized_stop = min(length - 1, normalized_stop)
        if normalized_start > normalized_stop:
            return 0
        removed = ordered[normalized_start:normalized_stop + 1]
        for member in removed:
            self.zsets[key].pop(member, None)
        return len(removed)

    def zrevrangebyscore(self, key, maximum, minimum, *, start, num):
        del minimum
        matching = [
            member for member, score in self.zsets.get(key, {}).items()
            if score <= float(maximum)
        ]
        matching.sort(key=lambda item: (self.zsets[key][item], _stream_tuple(item)), reverse=True)
        return matching[start:start + num]

    def xrange(self, key, min="-", max="+", count=None):
        del max
        if count is None:
            self.full_xrange_calls += 1
        else:
            self.bounded_xrange_calls += 1
        rows = list(self.streams.get(key, []))
        if min != "-":
            exclusive = str(min).startswith("(")
            boundary = _stream_tuple(str(min)[1:] if exclusive else str(min))
            if exclusive:
                rows = [row for row in rows if _stream_tuple(row[0]) > boundary]
            else:
                rows = [row for row in rows if _stream_tuple(row[0]) >= boundary]
        return rows[:count] if count is not None else rows

    def xrevrange(self, key, *, count):
        rows = list(reversed(self.streams.get(key, [])))
        return rows[:count]

    def xread(self, streams, *, count, block):
        del block
        self.xread_calls += 1
        if self.on_xread is not None:
            callback, self.on_xread = self.on_xread, None
            callback()
        key, start_id = next(iter(streams.items()))
        rows = [row for row in self.streams.get(key, []) if _stream_tuple(row[0]) > _stream_tuple(start_id)]
        return [(key, rows[:count])] if rows else []

    def hget(self, key, field):
        if key == "synthetic-activity":
            return self.activity.get(field)
        return self.hashes.get(key, {}).get(field)

    def hset(self, key, field, value):
        self.hashes.setdefault(key, {})[str(field)] = str(value)
        return 1

    def hmget(self, key, fields):
        return [self.hashes.get(key, {}).get(str(field)) for field in fields]


def _event(
    cursor: int,
    *,
    session_id: str = "tail-session",
    kind: str = "screenshot-capture-updated",
    performance: dict[str, object] | None = None,
):
    event = RealtimeEvent(
        event_id=f"event-{cursor}",
        session_id=session_id,
        owner_user_id="synthetic-user",
        kind=kind,
        payload={"status": "synthetic", **({"performance": performance} if performance else {})},
        created_at_ms=cursor,
    )
    return f"{cursor}-0", {"cursor": str(cursor), "event": json.dumps(asdict(event))}


def _repository(*, event_retention: int = 1_000):
    redis = SyntheticRedis()
    repository = object.__new__(RedisRealtimeSpeechRepository)
    repository._redis = redis
    repository._event_retention = event_retention
    repository._runtime_ttl_seconds = 7_200
    repository._activity_key = "synthetic-activity"
    return repository, redis


def test_long_indexed_stream_wait_does_not_full_scan_history() -> None:
    repository, redis = _repository()
    stream_key = "offersteady:realtime:events:tail-session"
    rows = [_event(cursor) for cursor in range(1, 1_001)]
    redis.streams[stream_key] = rows
    redis.activity["tail-session"] = 1_000
    repository._index_event_rows(session_id="tail-session", rows=rows)

    cursor, events, resumable = repository.wait_for_events_after(
        session_id="tail-session", cursor=1_000, timeout_ms=10
    )

    assert (cursor, events, resumable) == (1_000, [], True)
    assert redis.full_xrange_calls == 0
    assert redis.xread_calls == 1
    assert redis.bounded_xrange_calls == 2


def test_legacy_stream_scans_once_then_uses_cursor_index() -> None:
    repository, redis = _repository()
    stream_key = "offersteady:realtime:events:tail-session"
    rows = [_event(cursor) for cursor in range(1, 101)]
    redis.streams[stream_key] = rows
    redis.activity["tail-session"] = 100

    first = repository.list_events_after(session_id="tail-session", cursor=99)
    second = repository.list_events_after(session_id="tail-session", cursor=99)

    assert [event.event_id for event in first[1]] == ["event-100"]
    assert [event.event_id for event in second[1]] == ["event-100"]
    assert redis.full_xrange_calls == 1


def test_wait_decodes_xread_increment_without_post_wait_scan() -> None:
    repository, redis = _repository()
    stream_key = "offersteady:realtime:events:tail-session"
    rows = [_event(1)]
    redis.streams[stream_key] = rows
    redis.activity["tail-session"] = 1
    repository._index_event_rows(session_id="tail-session", rows=rows)

    def publish() -> None:
        redis.streams[stream_key].append(_event(2, performance={"traceId": "safe-trace"}))
        redis.activity["tail-session"] = 2

    redis.on_xread = publish
    cursor, events, resumable = repository.wait_for_events_after(
        session_id="tail-session", cursor=1, timeout_ms=100
    )

    assert cursor == 2
    assert resumable is True
    assert [event.event_id for event in events] == ["event-2"]
    assert events[0].payload["performance"]["redisReadMode"] == "xread"
    assert isinstance(events[0].payload["performance"]["redisEventXreadAtMs"], int)
    assert redis.full_xrange_calls == 0
    assert redis.xread_calls == 1


def test_cursor_older_than_retention_requests_snapshot_recovery() -> None:
    repository, redis = _repository()
    stream_key = "offersteady:realtime:events:tail-session"
    rows = [_event(cursor) for cursor in range(100, 111)]
    redis.streams[stream_key] = rows
    redis.activity["tail-session"] = 110

    cursor, events, resumable = repository.list_events_after(session_id="tail-session", cursor=5)

    assert cursor == 110
    assert events == []
    assert resumable is False
    assert redis.full_xrange_calls == 0


def test_cursor_index_is_bounded_to_event_retention() -> None:
    repository, redis = _repository(event_retention=3)
    rows = [_event(cursor) for cursor in range(1, 7)]
    repository._index_event_rows(session_id="tail-session", rows=rows)

    index = redis.zsets[repository._event_cursor_index_key("tail-session")]
    assert set(index) == {"4-0", "5-0", "6-0"}


def test_latest_event_cache_avoids_full_stream_scan_after_backfill() -> None:
    repository, redis = _repository()
    stream_key = "offersteady:realtime:events:tail-session"
    redis.streams[stream_key] = [
        _event(1, kind="degraded"),
        _event(2, kind="device-status"),
        _event(3, kind="degraded"),
    ]

    first = repository.list_latest_events_for_session(
        session_id="tail-session", kinds={"device-status", "degraded"}
    )
    second = repository.list_latest_events_for_session(
        session_id="tail-session", kinds={"device-status", "degraded"}
    )

    assert {item.kind: item.event_id for item in first} == {
        "degraded": "event-3",
        "device-status": "event-2",
    }
    assert {item.kind: item.event_id for item in second} == {
        "degraded": "event-3",
        "device-status": "event-2",
    }
    assert redis.full_xrange_calls == 1


def test_latest_event_cache_negative_entry_avoids_repeated_legacy_scans() -> None:
    repository, redis = _repository()
    stream_key = "offersteady:realtime:events:tail-session"
    redis.streams[stream_key] = [_event(1, kind="device-status")]

    first = repository.list_latest_events_for_session(
        session_id="tail-session", kinds={"device-status", "degraded"}
    )
    second = repository.list_latest_events_for_session(
        session_id="tail-session", kinds={"device-status", "degraded"}
    )

    assert [item.kind for item in first] == ["device-status"]
    assert [item.kind for item in second] == ["device-status"]
    assert redis.full_xrange_calls == 1


def test_session_stream_refreshes_only_event_specific_snapshots() -> None:
    screenshot = session_stream_refresh_plan(
        payload_type="update", event_kinds={"screenshot-capture-updated"}
    )
    transcript = session_stream_refresh_plan(
        payload_type="update", event_kinds={"transcript-updated"}
    )
    snapshot = session_stream_refresh_plan(payload_type="snapshot", event_kinds=set())

    assert screenshot == {"runtime": False, "transcripts": False, "candidates": False, "events": False}
    assert transcript == {"runtime": False, "transcripts": True, "candidates": False, "events": False}
    recovered_device = session_stream_refresh_plan(
        payload_type="update", event_kinds={"device-status"}
    )
    assert recovered_device["runtime"] is True
    assert snapshot == {"runtime": True, "transcripts": True, "candidates": True, "events": True}


def test_runtime_diagnostic_failure_does_not_close_transcript_sse() -> None:
    class RequestStub:
        app = SimpleNamespace(state=SimpleNamespace())

        async def is_disconnected(self) -> bool:
            return False

    partial = RealtimeEvent(
        event_id="partial-event-1",
        session_id="session-first-visible",
        owner_user_id="first-visible-owner",
        kind="transcript-updated",
        payload={
            "segmentId": "segment-first-visible",
            "sourceId": "system-loopback",
            "sourceKind": "system",
            "role": "interviewer",
            "revision": 1,
            "text": "synthetic partial",
            "isFinal": False,
            "transcriptConfidence": 0.9,
            "startedAtMs": 1,
            "endedAtMs": 2,
            "overlap": False,
        },
        created_at_ms=2,
    )

    class ServiceStub:
        settings = SimpleNamespace(realtime_event_block_ms=100)
        wait_calls = 0

        def require_active_realtime_session(self, **_kwargs) -> None:
            return None

        def list_session_events_after(self, **_kwargs):
            return 1, [], True

        def get_stream_bootstrap_state(self, **_kwargs):
            return (
                RealtimeTranscriptListResponse(sessionId="session-first-visible", transcripts=[]),
                RealtimeQuestionCandidateListResponse(sessionId="session-first-visible", candidates=[]),
                RealtimeEventListResponse(sessionId="session-first-visible", events=[]),
            )

        def get_runtime(self, **_kwargs):
            raise RuntimeError("synthetic runtime diagnostic failure")

        def wait_for_session_events_after(self, **_kwargs):
            self.wait_calls += 1
            return 2, [partial], True

        def observe_sse_delivery(self, events, *, sent_at_ms):
            del sent_at_ms
            return events

        def event_response(self, event):
            return RealtimeEventResponse(
                eventId=event.event_id,
                kind=event.kind,
                payload=event.payload,
                createdAtMs=event.created_at_ms,
            )

    async def scenario() -> tuple[str, str, int]:
        service = ServiceStub()
        response = await stream_session_runtime(
            "session-first-visible",
            RequestStub(),
            user_id="first-visible-owner",
            cursor=0,
            page_instance_id=None,
            lease_generation=None,
            auth_context=None,
            service=service,
        )
        iterator = response.body_iterator
        first = await iterator.__anext__()
        second = await iterator.__anext__()
        await iterator.aclose()
        return str(first), str(second), service.wait_calls

    first, second, wait_calls = asyncio.run(scenario())

    assert 'event: snapshot' in first
    assert 'event: update' in second
    assert 'partial-event-1' in second
    assert wait_calls == 1


def test_sse_batch_keeps_only_latest_revision_per_transcript_segment() -> None:
    def event(event_id: str, kind: str, *, segment_id: str | None = None, revision: int = 1, is_final: bool = False) -> RealtimeEvent:
        payload: dict[str, object] = {"revision": revision, "isFinal": is_final}
        if segment_id is not None:
            payload["segmentId"] = segment_id
        return RealtimeEvent(
            event_id=event_id,
            session_id="tail-session",
            owner_user_id="synthetic-user",
            kind=kind,
            payload=payload,
            created_at_ms=revision,
        )

    coalesced = coalesce_transcript_revisions([
        event("partial-a-1", "transcript-updated", segment_id="segment-a", revision=1),
        event("answer-started", "answer-task-updated"),
        event("partial-b-1", "transcript-updated", segment_id="segment-b", revision=1),
        event("partial-a-2", "transcript-updated", segment_id="segment-a", revision=2),
        event("final-b-2", "transcript-updated", segment_id="segment-b", revision=2, is_final=True),
        event("late-partial-b-3", "transcript-updated", segment_id="segment-b", revision=3),
    ])

    assert [item.event_id for item in coalesced] == ["answer-started", "partial-a-2", "final-b-2"]


def test_blocking_wait_executor_does_not_starve_default_executor() -> None:
    async def scenario() -> float:
        executor = RealtimeEventWaitExecutor(max_workers=1)
        release = threading.Event()
        blocked = asyncio.create_task(executor.run(lambda: release.wait(1.0)))
        await asyncio.sleep(0.02)
        started = time.perf_counter()
        assert await asyncio.to_thread(lambda: "ordinary-api") == "ordinary-api"
        elapsed_ms = (time.perf_counter() - started) * 1_000
        release.set()
        await blocked
        executor.shutdown()
        return elapsed_ms

    assert asyncio.run(scenario()) < 100
