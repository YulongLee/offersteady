from __future__ import annotations

import json
import threading
import time
from dataclasses import asdict, replace
from typing import Callable, TypeVar

from redis import Redis
import psycopg

from app.core.config import Settings
from app.ports.realtime_speech import (
    AccountDesktopDeviceRecord,
    AsrUsageReport,
    DesktopDeviceRecord,
    QuestionCandidateRecord,
    RealtimeEvent,
    RealtimeFrameReceiptRecord,
    RealtimePublisherRecord,
    SessionDesktopBindingRecord,
    TranscriptSegmentRecord,
    WebSessionHeartbeatRecord,
)
from app.services.realtime_speech_repository import InMemoryRealtimeSpeechRepository


T = TypeVar("T")


class RedisRealtimeSpeechRepository(InMemoryRealtimeSpeechRepository):
    """Shared Redis-backed runtime repository with atomic snapshot updates.

    Raw audio is never included. Redis contains only leases, bindings, receipts,
    transcript metadata and bounded operational events needed for recovery.
    """

    def __init__(self, settings: Settings) -> None:
        super().__init__(state_file=None)
        if not settings.redis_url:
            raise ValueError("redis_url_required")
        self._redis = Redis.from_url(
            settings.redis_url,
            decode_responses=True,
            socket_timeout=settings.redis_socket_timeout_seconds,
            socket_connect_timeout=settings.redis_socket_timeout_seconds,
            health_check_interval=15,
        )
        self._snapshot_key = "offersteady:realtime:runtime:v2"
        self._lock_key = f"{self._snapshot_key}:lock"
        self._receipt_key = f"{self._snapshot_key}:receipts"
        self._publisher_key = f"{self._snapshot_key}:publishers"
        self._publisher_token_key = f"{self._snapshot_key}:publisher-tokens"
        self._transcript_key = f"{self._snapshot_key}:transcripts"
        self._activity_key = f"{self._snapshot_key}:activity"
        self._runtime_lock = threading.RLock()
        self._event_retention = max(100, settings.realtime_event_retention)
        self._runtime_ttl_seconds = max(300, settings.realtime_runtime_ttl_seconds)
        self._settings = settings
        self._event_diagnostic_lock = threading.Lock()
        self._event_diagnostics = {
            "xaddCount": 0,
            "xaddLatestMs": 0,
            "xaddMaxMs": 0,
            "xreadCount": 0,
            "xreadLatestMs": 0,
            "xreadMaxMs": 0,
            "eventLatestLagMs": 0,
            "streamLength": 0,
            "pendingEvents": 0,
            "pendingApplicable": False,
            "consumerMode": "xread-no-group",
        }
        self._redis.ping()
        self._reload()

    def _snapshot(self) -> dict[str, object]:
        return {
            # Publishers are stored as entity-scoped hashes. Keep this field empty
            # so an audio lifecycle update never expands the global snapshot.
            "publishers": [],
            "receipts": [],
            "transcripts": [],
            "candidates": [asdict(item) for item in self.candidates.values()],
            "events": [],
            "activity": self.session_activity_versions,
            "devices": [asdict(item) for item in self.desktop_devices_by_id.values()],
            "accountDevices": [asdict(item) for item in self.account_desktop_devices.values()],
            "bindings": [asdict(item) for item in self.session_bindings.values()],
            "heartbeats": [asdict(item) for item in self.web_session_heartbeats.values()],
        }

    def _ensure_event_diagnostics(self) -> None:
        if hasattr(self, "_event_diagnostic_lock"):
            return
        self._event_diagnostic_lock = threading.Lock()
        self._event_diagnostics = {
            "xaddCount": 0,
            "xaddLatestMs": 0,
            "xaddMaxMs": 0,
            "xreadCount": 0,
            "xreadLatestMs": 0,
            "xreadMaxMs": 0,
            "eventLatestLagMs": 0,
            "streamLength": 0,
            "pendingEvents": 0,
            "pendingApplicable": False,
            "consumerMode": "xread-no-group",
        }

    def _reload(self) -> None:
        raw = self._redis.get(self._snapshot_key)
        if not raw:
            return
        payload = json.loads(raw)
        self.publishers_by_id = {}
        self.publishers_by_token = {}
        legacy_publishers = payload.get("publishers", [])
        for item in legacy_publishers:
            record = RealtimePublisherRecord(**item)
            self.publishers_by_id[record.publisher_id] = record
            self.publishers_by_token[record.token] = record.publisher_id
        if legacy_publishers:
            # One-time, idempotent migration keeps reconnect tokens valid while
            # publisher lifecycle updates move away from the global snapshot.
            pipeline = self._redis.pipeline()
            for item in legacy_publishers:
                record = RealtimePublisherRecord(**item)
                pipeline.hset(
                    self._publisher_key,
                    record.publisher_id,
                    json.dumps(asdict(record), ensure_ascii=True, separators=(",", ":")),
                )
                pipeline.hset(self._publisher_token_key, record.token, record.publisher_id)
            pipeline.expire(self._publisher_key, self._runtime_ttl_seconds)
            pipeline.expire(self._publisher_token_key, self._runtime_ttl_seconds)
            pipeline.execute()
        for _publisher_id, raw_publisher in self._redis.hscan_iter(self._publisher_key):
            record = RealtimePublisherRecord(**json.loads(raw_publisher))
            self.publishers_by_id[record.publisher_id] = record
            self.publishers_by_token[record.token] = record.publisher_id
        self.frame_receipts = {}
        for item in payload.get("receipts", []):
            record = RealtimeFrameReceiptRecord(**item)
            self.frame_receipts.setdefault(record.session_id, {})[(record.source_kind, record.source_id)] = record
        self.transcripts = {}
        for item in payload.get("transcripts", []):
            usage = item.get("usage")
            if isinstance(usage, dict):
                item["usage"] = AsrUsageReport(**usage)
            record = TranscriptSegmentRecord(**item)
            self.transcripts.setdefault(record.session_id, {})[record.segment_id] = record
        self.candidates = {}
        for item in payload.get("candidates", []):
            record = QuestionCandidateRecord(**item)
            self.candidates[record.candidate_id] = record
        self.events = {}
        for item in payload.get("events", []):
            record = RealtimeEvent(**item)
            self.events.setdefault(record.session_id, []).append(record)
        self.session_activity_versions = {str(key): int(value) for key, value in payload.get("activity", {}).items()}
        for session_id, version in self._redis.hgetall(self._activity_key).items():
            self.session_activity_versions[session_id] = max(
                self.session_activity_versions.get(session_id, 0),
                int(version),
            )
        self.desktop_devices_by_id = {}
        self.desktop_devices_by_code = {}
        for item in payload.get("devices", []):
            record = DesktopDeviceRecord(**item)
            self.desktop_devices_by_id[record.device_id] = record
            self.desktop_devices_by_code[record.manual_code] = record.device_id
        self.account_desktop_devices = {}
        for item in payload.get("accountDevices", []):
            record = AccountDesktopDeviceRecord(**item)
            self.account_desktop_devices[(record.owner_user_id, record.device_id)] = record
        self.session_bindings = {}
        for item in payload.get("bindings", []):
            record = SessionDesktopBindingRecord(**item)
            self.session_bindings[(record.owner_user_id, record.session_id)] = record
        if not self.account_desktop_devices:
            for binding in self.session_bindings.values():
                key = (binding.owner_user_id, binding.device_id)
                current = self.account_desktop_devices.get(key)
                self.account_desktop_devices[key] = AccountDesktopDeviceRecord(
                    owner_user_id=binding.owner_user_id,
                    device_id=binding.device_id,
                    manual_code=binding.manual_code,
                    linked_at_ms=min(current.linked_at_ms, binding.bound_at_ms) if current else binding.bound_at_ms,
                    last_used_at_ms=max(current.last_used_at_ms, binding.bound_at_ms) if current else binding.bound_at_ms,
                )
        self.web_session_heartbeats = {}
        for item in payload.get("heartbeats", []):
            record = WebSessionHeartbeatRecord(**item)
            self.web_session_heartbeats[(record.owner_user_id, record.session_id)] = record

    def _read(self, operation: Callable[[], T]) -> T:
        with self._runtime_lock:
            if self._settings.realtime_redis_snapshot_reload_on_access:
                self._reload()
            return operation()

    def _write(self, operation: Callable[[], T]) -> T:
        with self._redis.lock(self._lock_key, timeout=5, blocking_timeout=2):
            with self._runtime_lock:
                if self._settings.realtime_redis_snapshot_reload_on_access:
                    self._reload()
                result = operation()
                self._redis.set(self._snapshot_key, json.dumps(self._snapshot(), ensure_ascii=True, separators=(",", ":")))
                self._redis.expire(self._snapshot_key, self._runtime_ttl_seconds)
                if self.session_activity_versions:
                    self._redis.hset(self._activity_key, mapping=self.session_activity_versions)
                    self._redis.expire(self._activity_key, self._runtime_ttl_seconds)
                return result

    def save_desktop_device(self, device): return self._write(lambda: super(RedisRealtimeSpeechRepository, self).save_desktop_device(device))
    def get_desktop_device_by_code(self, manual_code): return self._read(lambda: super(RedisRealtimeSpeechRepository, self).get_desktop_device_by_code(manual_code))
    def save_account_desktop_device(self, association): return self._write(lambda: super(RedisRealtimeSpeechRepository, self).save_account_desktop_device(association))
    def get_account_desktop_device(self, *, user_id, device_id): return self._read(lambda: super(RedisRealtimeSpeechRepository, self).get_account_desktop_device(user_id=user_id, device_id=device_id))
    def get_last_account_desktop_device(self, *, user_id): return self._read(lambda: super(RedisRealtimeSpeechRepository, self).get_last_account_desktop_device(user_id=user_id))
    def list_account_desktop_devices(self, *, user_id): return self._read(lambda: super(RedisRealtimeSpeechRepository, self).list_account_desktop_devices(user_id=user_id))
    def save_session_desktop_binding(self, binding): return self._write(lambda: super(RedisRealtimeSpeechRepository, self).save_session_desktop_binding(binding))
    def get_session_desktop_binding(self, *, user_id, session_id): return self._read(lambda: super(RedisRealtimeSpeechRepository, self).get_session_desktop_binding(user_id=user_id, session_id=session_id))
    def get_latest_session_desktop_binding_for_device(self, *, device_id, manual_code): return self._read(lambda: super(RedisRealtimeSpeechRepository, self).get_latest_session_desktop_binding_for_device(device_id=device_id, manual_code=manual_code))
    def get_latest_session_desktop_binding_by_code(self, *, manual_code): return self._read(lambda: super(RedisRealtimeSpeechRepository, self).get_latest_session_desktop_binding_by_code(manual_code=manual_code))
    def list_session_desktop_bindings_for_device(self, *, device_id, manual_code): return self._read(lambda: super(RedisRealtimeSpeechRepository, self).list_session_desktop_bindings_for_device(device_id=device_id, manual_code=manual_code))
    def list_session_desktop_bindings_for_user(self, *, user_id): return self._read(lambda: super(RedisRealtimeSpeechRepository, self).list_session_desktop_bindings_for_user(user_id=user_id))
    def save_web_session_heartbeat(self, heartbeat): return self._write(lambda: super(RedisRealtimeSpeechRepository, self).save_web_session_heartbeat(heartbeat))
    def get_web_session_heartbeat(self, *, user_id, session_id): return self._read(lambda: super(RedisRealtimeSpeechRepository, self).get_web_session_heartbeat(user_id=user_id, session_id=session_id))
    def claim_live_web_session(self, heartbeat): return self._write(lambda: super(RedisRealtimeSpeechRepository, self).claim_live_web_session(heartbeat))
    def get_active_live_web_session(self, *, user_id): return self._read(lambda: super(RedisRealtimeSpeechRepository, self).get_active_live_web_session(user_id=user_id))
    def save_publisher(self, publisher):
        with self._runtime_lock:
            stored = super().save_publisher(publisher)
        payload = json.dumps(asdict(stored), ensure_ascii=True, separators=(",", ":"))
        pipeline = self._redis.pipeline()
        pipeline.hset(self._publisher_key, stored.publisher_id, payload)
        pipeline.hset(self._publisher_token_key, stored.token, stored.publisher_id)
        pipeline.expire(self._publisher_key, self._runtime_ttl_seconds)
        pipeline.expire(self._publisher_token_key, self._runtime_ttl_seconds)
        pipeline.execute()
        return stored

    def get_publisher_by_token(self, token):
        publisher_id = self._redis.hget(self._publisher_token_key, token)
        if publisher_id:
            return self.get_publisher(publisher_id)
        return self._read(lambda: super(RedisRealtimeSpeechRepository, self).get_publisher_by_token(token))

    def get_publisher(self, publisher_id):
        raw = self._redis.hget(self._publisher_key, publisher_id)
        if raw:
            return RealtimePublisherRecord(**json.loads(raw))
        return self._read(lambda: super(RedisRealtimeSpeechRepository, self).get_publisher(publisher_id))

    def list_publishers_for_session(self, *, session_id):
        records = []
        for _field, raw in self._redis.hscan_iter(self._publisher_key):
            payload = json.loads(raw)
            if payload.get("session_id") == session_id:
                records.append(RealtimePublisherRecord(**payload))
        if records:
            return sorted(records, key=lambda item: item.issued_at_ms)
        return self._read(lambda: super(RedisRealtimeSpeechRepository, self).list_publishers_for_session(session_id=session_id))

    def prune_publishers_for_session(self, *, session_id, keep_publisher_ids):
        removable = [
            item for item in self.list_publishers_for_session(session_id=session_id)
            if item.publisher_id not in keep_publisher_ids
        ]
        if not removable:
            return None
        with self._runtime_lock:
            super().prune_publishers_for_session(session_id=session_id, keep_publisher_ids=keep_publisher_ids)
        pipeline = self._redis.pipeline()
        for item in removable:
            pipeline.hdel(self._publisher_key, item.publisher_id)
            pipeline.hdel(self._publisher_token_key, item.token)
        pipeline.execute()
        return None
    def save_frame_receipt(self, receipt):
        with self._runtime_lock:
            stored = super().save_frame_receipt(receipt)
        field = f"{stored.session_id}:{stored.source_kind}:{stored.source_id}"
        self._redis.hset(self._receipt_key, field, json.dumps(asdict(stored), ensure_ascii=True, separators=(",", ":")))
        self._redis.expire(self._receipt_key, self._runtime_ttl_seconds)
        return stored

    def get_frame_receipt(self, *, session_id, source_kind, source_id):
        raw = self._redis.hget(self._receipt_key, f"{session_id}:{source_kind}:{source_id}")
        if raw:
            return RealtimeFrameReceiptRecord(**json.loads(raw))
        return None

    def list_frame_receipts_for_session(self, *, session_id):
        prefix = f"{session_id}:"
        records = [
            RealtimeFrameReceiptRecord(**json.loads(raw))
            for field, raw in self._redis.hscan_iter(self._receipt_key, match=f"{prefix}*")
        ]
        return sorted(records, key=lambda item: (item.source_kind, item.source_id))

    def save_transcript(self, segment):
        with self._runtime_lock:
            persisted_version = self._redis.hget(self._activity_key, segment.session_id)
            if persisted_version is not None:
                self.session_activity_versions[segment.session_id] = max(
                    self.session_activity_versions.get(segment.session_id, 0),
                    int(persisted_version),
                )
            stored = super().save_transcript(segment)
            activity_version = self.session_activity_versions.get(stored.session_id, 0)
        field = f"{stored.session_id}:{stored.segment_id}"
        self._redis.hset(self._transcript_key, field, json.dumps(asdict(stored), ensure_ascii=True, separators=(",", ":")))
        self._redis.expire(self._transcript_key, self._runtime_ttl_seconds)
        self._redis.hset(self._activity_key, stored.session_id, activity_version)
        self._redis.expire(self._activity_key, self._runtime_ttl_seconds)
        return stored

    def persist_transcript(self, stored):
        if stored.is_final and self._settings.realtime_transcript_persistence_enabled and self._settings.database_url:
            expires_at_ms = int(time.time() * 1000) + self._settings.realtime_transcript_retention_days * 86_400_000
            with psycopg.connect(self._settings.database_url) as connection:
                with connection.cursor() as cursor:
                    cursor.execute(
                        """
                        INSERT INTO approved_realtime_transcripts
                          (session_id, owner_user_id, segment_id, role, transcript_text, created_at_ms, expires_at_ms)
                        VALUES (%s, %s, %s, %s, %s, %s, %s)
                        ON CONFLICT (session_id, segment_id) DO UPDATE SET
                          role = EXCLUDED.role,
                          transcript_text = EXCLUDED.transcript_text,
                          expires_at_ms = EXCLUDED.expires_at_ms
                        """,
                        (stored.session_id, stored.owner_user_id, stored.segment_id, stored.role, stored.text, stored.created_at_ms, expires_at_ms),
                    )
        return None

    @staticmethod
    def _decode_transcript(raw: str) -> TranscriptSegmentRecord:
        payload = json.loads(raw)
        usage = payload.get("usage")
        if isinstance(usage, dict):
            payload["usage"] = AsrUsageReport(**usage)
        return TranscriptSegmentRecord(**payload)

    def get_transcript(self, session_id, segment_id):
        raw = self._redis.hget(self._transcript_key, f"{session_id}:{segment_id}")
        return self._decode_transcript(raw) if raw else None

    def list_transcripts_for_session(self, *, session_id):
        records = [
            self._decode_transcript(raw)
            for _field, raw in self._redis.hscan_iter(self._transcript_key, match=f"{session_id}:*")
        ]
        return sorted(records, key=lambda item: (item.started_at_ms, item.segment_id, item.revision))
    def save_candidate(self, candidate): return self._write(lambda: super(RedisRealtimeSpeechRepository, self).save_candidate(candidate))
    def get_candidate(self, candidate_id): return self._read(lambda: super(RedisRealtimeSpeechRepository, self).get_candidate(candidate_id))
    def list_candidates_for_session(self, *, session_id): return self._read(lambda: super(RedisRealtimeSpeechRepository, self).list_candidates_for_session(session_id=session_id))

    def save_event(self, event):
        with self._runtime_lock:
            stored = super().save_event(event)
        stream_key = f"offersteady:realtime:events:{stored.session_id}"
        cursor_index_key = self._event_cursor_index_key(stored.session_id)
        cursor = self.session_activity_versions.get(stored.session_id, 0)
        xadd_started_at_ms = int(time.time() * 1000)
        xadd_started = time.perf_counter()
        stream_id = self._redis.xadd(
            stream_key,
            {"cursor": str(cursor), "event": json.dumps(asdict(stored), ensure_ascii=True)},
            maxlen=self._event_retention,
            approximate=True,
        )
        xadd_completed_at_ms = int(time.time() * 1000)
        xadd_ms = max(0, int((time.perf_counter() - xadd_started) * 1000))
        self._ensure_event_diagnostics()
        with self._event_diagnostic_lock:
            self._event_diagnostics["xaddCount"] += 1
            self._event_diagnostics["xaddLatestMs"] = xadd_ms
            self._event_diagnostics["xaddMaxMs"] = max(self._event_diagnostics["xaddMaxMs"], xadd_ms)
        pipeline = self._redis.pipeline()
        pipeline.zadd(cursor_index_key, {stream_id: cursor})
        pipeline.hset(
            self._latest_event_key(stored.session_id),
            stored.kind,
            json.dumps(asdict(stored), ensure_ascii=True),
        )
        pipeline.zremrangebyrank(cursor_index_key, 0, -(self._event_retention + 1))
        pipeline.expire(cursor_index_key, self._runtime_ttl_seconds)
        pipeline.expire(self._latest_event_key(stored.session_id), self._runtime_ttl_seconds)
        pipeline.expire(stream_key, self._runtime_ttl_seconds)
        pipeline.execute()
        performance = stored.payload.get("performance")
        if not isinstance(performance, dict):
            return stored
        return replace(
            stored,
            payload={
                **stored.payload,
                "performance": {
                    **performance,
                    "redisEventXaddStartAtMs": xadd_started_at_ms,
                    "redisEventXaddCompleteAtMs": xadd_completed_at_ms,
                    "redisEventXaddAtMs": xadd_completed_at_ms,
                    "redisEventXaddDurationMs": xadd_ms,
                },
            },
        )

    @staticmethod
    def _event_cursor_index_key(session_id: str) -> str:
        return f"offersteady:realtime:event-cursors:{session_id}"

    @staticmethod
    def _latest_event_key(session_id: str) -> str:
        return f"offersteady:realtime:latest-events:{session_id}"

    @staticmethod
    def _decode_event_rows(rows) -> list[tuple[int, RealtimeEvent]]:
        decoded: list[tuple[int, RealtimeEvent]] = []
        for _stream_id, fields in rows:
            raw = fields.get("event")
            if not raw:
                continue
            decoded.append((int(fields.get("cursor", "0")), RealtimeEvent(**json.loads(raw))))
        return decoded

    @staticmethod
    def _mark_events_read(
        events: list[RealtimeEvent], *, read_at_ms: int, mode: str
    ) -> list[RealtimeEvent]:
        enriched: list[RealtimeEvent] = []
        for event in events:
            performance = event.payload.get("performance")
            if not isinstance(performance, dict):
                enriched.append(event)
                continue
            enriched.append(replace(
                event,
                payload={
                    **event.payload,
                    "performance": {
                        **performance,
                        "redisEventXreadAtMs": read_at_ms,
                        "redisReadMode": mode,
                    },
                },
            ))
        return enriched

    def _record_stream_read(
        self,
        *,
        stream_key: str,
        events: list[RealtimeEvent],
        read_ms: int,
        elapsed_ms: int,
        mode: str,
    ) -> None:
        latest_lag_ms = max(
            (max(0, read_ms - event.created_at_ms) for event in events),
            default=0,
        )
        xlen = getattr(self._redis, "xlen", None)
        stream_length = int(xlen(stream_key)) if callable(xlen) else -1
        self._ensure_event_diagnostics()
        with self._event_diagnostic_lock:
            if mode == "xread":
                self._event_diagnostics["xreadCount"] += 1
                self._event_diagnostics["xreadLatestMs"] = elapsed_ms
                self._event_diagnostics["xreadMaxMs"] = max(self._event_diagnostics["xreadMaxMs"], elapsed_ms)
            self._event_diagnostics["eventLatestLagMs"] = latest_lag_ms
            self._event_diagnostics["streamLength"] = stream_length
            # XREAD is deliberately used without a consumer group. XPENDING is
            # therefore not applicable and must not be reported as hidden work.
            self._event_diagnostics["pendingEvents"] = 0
            self._event_diagnostics["pendingApplicable"] = False
            self._event_diagnostics["consumerMode"] = "xread-no-group"

    def _index_event_rows(self, *, session_id: str, rows) -> None:
        mapping = {
            stream_id: int(fields.get("cursor", "0"))
            for stream_id, fields in rows
            if int(fields.get("cursor", "0")) > 0
        }
        if not mapping:
            return
        cursor_index_key = self._event_cursor_index_key(session_id)
        pipeline = self._redis.pipeline()
        pipeline.zadd(cursor_index_key, mapping)
        pipeline.zremrangebyrank(cursor_index_key, 0, -(self._event_retention + 1))
        pipeline.expire(cursor_index_key, self._runtime_ttl_seconds)
        pipeline.execute()

    def _stream_id_at_or_before_cursor(self, *, session_id: str, cursor: int) -> str | None:
        values = self._redis.zrevrangebyscore(
            self._event_cursor_index_key(session_id),
            cursor,
            "-inf",
            start=0,
            num=1,
        )
        return str(values[0]) if values else None

    def _legacy_stream_id_at_or_before_cursor(self, *, session_id: str, cursor: int) -> str | None:
        rows = self._redis.xrange(f"offersteady:realtime:events:{session_id}")
        self._index_event_rows(session_id=session_id, rows=rows)
        matching = [
            stream_id
            for stream_id, fields in rows
            if int(fields.get("cursor", "0")) <= cursor
        ]
        return str(matching[-1]) if matching else None

    def _stream_bounds(self, *, session_id: str) -> tuple[int | None, int]:
        stream_key = f"offersteady:realtime:events:{session_id}"
        first_rows = self._redis.xrange(stream_key, count=1)
        current_cursor = self.get_event_stream_version(session_id=session_id)
        if not first_rows:
            return None, current_cursor
        return int(first_rows[0][1].get("cursor", "0")), current_cursor

    def list_events_for_session(self, *, session_id):
        return [
            event for _cursor, event in self._decode_event_rows(
                self._redis.xrange(f"offersteady:realtime:events:{session_id}")
            )
        ]

    def list_latest_events_for_session(self, *, session_id: str, kinds: set[str]):
        if not kinds:
            return []
        ordered_kinds = sorted(kinds)
        cache_key = self._latest_event_key(session_id)
        raw_values = self._redis.hmget(cache_key, ordered_kinds)
        cached = dict(zip(ordered_kinds, raw_values, strict=True))
        latest = {
            kind: RealtimeEvent(**json.loads(raw))
            for kind, raw in cached.items()
            if raw is not None and raw != "null"
        }
        missing = {kind for kind, raw in cached.items() if raw is None}
        if missing:
            for item in reversed(self.list_events_for_session(session_id=session_id)):
                if item.kind in missing:
                    latest[item.kind] = item
                    missing.remove(item.kind)
                    if not missing:
                        break
            pipeline = self._redis.pipeline()
            for kind in kinds:
                item = latest.get(kind)
                pipeline.hset(
                    cache_key,
                    kind,
                    json.dumps(asdict(item), ensure_ascii=True) if item is not None else "null",
                )
            pipeline.expire(cache_key, self._runtime_ttl_seconds)
            pipeline.execute()
        return [latest[kind] for kind in ordered_kinds if kind in latest]

    def list_events_after(self, *, session_id: str, cursor: int) -> tuple[int, list[RealtimeEvent], bool]:
        stream_key = f"offersteady:realtime:events:{session_id}"
        first_cursor, current_cursor = self._stream_bounds(session_id=session_id)
        if first_cursor is None:
            return current_cursor, [], True
        resumable = cursor <= 0 or cursor >= first_cursor - 1
        if not resumable:
            return current_cursor, [], False
        if cursor <= 0:
            rows = self._redis.xrange(stream_key, count=self._event_retention)
        else:
            start_id = self._stream_id_at_or_before_cursor(session_id=session_id, cursor=cursor)
            if start_id is None:
                start_id = self._legacy_stream_id_at_or_before_cursor(session_id=session_id, cursor=cursor)
            rows = self._redis.xrange(
                stream_key,
                min=f"({start_id}" if start_id else "-",
                count=self._event_retention,
            )
        read_at_ms = int(time.time() * 1000)
        retained = self._decode_event_rows(rows)
        events = [item for item_cursor, item in retained if item_cursor > cursor]
        if events:
            self._record_stream_read(
                stream_key=stream_key,
                events=events,
                read_ms=read_at_ms,
                elapsed_ms=0,
                mode="xrange",
            )
        return current_cursor, self._mark_events_read(events, read_at_ms=read_at_ms, mode="xrange"), True

    def wait_for_events_after(
        self, *, session_id: str, cursor: int, timeout_ms: int
    ) -> tuple[int, list[RealtimeEvent], bool]:
        immediate = self.list_events_after(session_id=session_id, cursor=cursor)
        if immediate[1] or not immediate[2] or timeout_ms <= 0:
            return immediate
        stream_key = f"offersteady:realtime:events:{session_id}"
        start_id = self._stream_id_at_or_before_cursor(session_id=session_id, cursor=cursor)
        if start_id is None:
            start_id = self._legacy_stream_id_at_or_before_cursor(session_id=session_id, cursor=cursor) or "0-0"
        xread_started = time.perf_counter()
        streams = self._redis.xread(
            {stream_key: start_id},
            count=self._event_retention,
            block=max(1, timeout_ms),
        )
        xread_ms = max(0, int((time.perf_counter() - xread_started) * 1000))
        rows = streams[0][1] if streams else []
        read_at_ms = int(time.time() * 1000)
        retained = self._decode_event_rows(rows)
        events = [item for item_cursor, item in retained if item_cursor > cursor]
        self._record_stream_read(
            stream_key=stream_key,
            events=events,
            read_ms=read_at_ms,
            elapsed_ms=xread_ms,
            mode="xread",
        )
        current_cursor = max(
            self.get_event_stream_version(session_id=session_id),
            max((item_cursor for item_cursor, _event in retained), default=cursor),
        )
        return current_cursor, self._mark_events_read(events, read_at_ms=read_at_ms, mode="xread"), True

    def operational_diagnostics(self) -> dict[str, object]:
        self._ensure_event_diagnostics()
        with self._event_diagnostic_lock:
            return dict(self._event_diagnostics)

    def get_session_activity_version(self, *, session_id):
        activity_version = int(self._redis.hget(self._activity_key, session_id) or 0)
        items = self._redis.xrevrange(f"offersteady:realtime:events:{session_id}", count=1)
        event_version = int(items[0][1].get("cursor", "0")) if items else 0
        return max(activity_version, event_version)

    def get_event_stream_version(self, *, session_id: str) -> int:
        return self.get_session_activity_version(session_id=session_id)

    def readiness(self) -> bool:
        return bool(self._redis.ping())
