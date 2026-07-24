from __future__ import annotations

import json
import threading
import time
from dataclasses import asdict
from typing import Callable, TypeVar

from redis import Redis
import psycopg

from app.core.config import Settings
from app.ports.realtime_speech import (
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
        self._transcript_key = f"{self._snapshot_key}:transcripts"
        self._runtime_lock = threading.RLock()
        self._event_retention = max(100, settings.realtime_event_retention)
        self._runtime_ttl_seconds = max(300, settings.realtime_runtime_ttl_seconds)
        self._settings = settings
        self._redis.ping()
        self._reload()

    def _snapshot(self) -> dict[str, object]:
        return {
            "publishers": [asdict(item) for item in self.publishers_by_id.values()],
            "receipts": [],
            "transcripts": [],
            "candidates": [asdict(item) for item in self.candidates.values()],
            "events": [],
            "activity": self.session_activity_versions,
            "devices": [asdict(item) for item in self.desktop_devices_by_id.values()],
            "bindings": [asdict(item) for item in self.session_bindings.values()],
            "heartbeats": [asdict(item) for item in self.web_session_heartbeats.values()],
        }

    def _reload(self) -> None:
        raw = self._redis.get(self._snapshot_key)
        if not raw:
            return
        payload = json.loads(raw)
        self.publishers_by_id = {}
        self.publishers_by_token = {}
        for item in payload.get("publishers", []):
            record = RealtimePublisherRecord(**item)
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
        self.desktop_devices_by_id = {}
        self.desktop_devices_by_code = {}
        for item in payload.get("devices", []):
            record = DesktopDeviceRecord(**item)
            self.desktop_devices_by_id[record.device_id] = record
            self.desktop_devices_by_code[record.manual_code] = record.device_id
        self.session_bindings = {}
        for item in payload.get("bindings", []):
            record = SessionDesktopBindingRecord(**item)
            self.session_bindings[(record.owner_user_id, record.session_id)] = record
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
                return result

    def save_desktop_device(self, device): return self._write(lambda: super(RedisRealtimeSpeechRepository, self).save_desktop_device(device))
    def get_desktop_device_by_code(self, manual_code): return self._read(lambda: super(RedisRealtimeSpeechRepository, self).get_desktop_device_by_code(manual_code))
    def save_session_desktop_binding(self, binding): return self._write(lambda: super(RedisRealtimeSpeechRepository, self).save_session_desktop_binding(binding))
    def get_session_desktop_binding(self, *, user_id, session_id): return self._read(lambda: super(RedisRealtimeSpeechRepository, self).get_session_desktop_binding(user_id=user_id, session_id=session_id))
    def get_latest_session_desktop_binding_for_device(self, *, device_id, manual_code): return self._read(lambda: super(RedisRealtimeSpeechRepository, self).get_latest_session_desktop_binding_for_device(device_id=device_id, manual_code=manual_code))
    def get_latest_session_desktop_binding_by_code(self, *, manual_code): return self._read(lambda: super(RedisRealtimeSpeechRepository, self).get_latest_session_desktop_binding_by_code(manual_code=manual_code))
    def save_web_session_heartbeat(self, heartbeat): return self._write(lambda: super(RedisRealtimeSpeechRepository, self).save_web_session_heartbeat(heartbeat))
    def get_web_session_heartbeat(self, *, user_id, session_id): return self._read(lambda: super(RedisRealtimeSpeechRepository, self).get_web_session_heartbeat(user_id=user_id, session_id=session_id))
    def save_publisher(self, publisher): return self._write(lambda: super(RedisRealtimeSpeechRepository, self).save_publisher(publisher))
    def get_publisher_by_token(self, token): return self._read(lambda: super(RedisRealtimeSpeechRepository, self).get_publisher_by_token(token))
    def get_publisher(self, publisher_id): return self._read(lambda: super(RedisRealtimeSpeechRepository, self).get_publisher(publisher_id))
    def list_publishers_for_session(self, *, session_id): return self._read(lambda: super(RedisRealtimeSpeechRepository, self).list_publishers_for_session(session_id=session_id))
    def save_frame_receipt(self, receipt):
        with self._runtime_lock:
            stored = super().save_frame_receipt(receipt)
        field = f"{stored.session_id}:{stored.source_kind}:{stored.source_id}"
        self._redis.hset(self._receipt_key, field, json.dumps(asdict(stored), ensure_ascii=True, separators=(",", ":")))
        self._redis.expire(self._receipt_key, self._runtime_ttl_seconds)
        return stored

    def list_frame_receipts_for_session(self, *, session_id):
        prefix = f"{session_id}:"
        records = [
            RealtimeFrameReceiptRecord(**json.loads(raw))
            for field, raw in self._redis.hscan_iter(self._receipt_key, match=f"{prefix}*")
        ]
        return sorted(records, key=lambda item: (item.source_kind, item.source_id))

    def save_transcript(self, segment):
        with self._runtime_lock:
            stored = super().save_transcript(segment)
        field = f"{stored.session_id}:{stored.segment_id}"
        self._redis.hset(self._transcript_key, field, json.dumps(asdict(stored), ensure_ascii=True, separators=(",", ":")))
        self._redis.expire(self._transcript_key, self._runtime_ttl_seconds)
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
        return stored

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
        cursor = self.session_activity_versions.get(stored.session_id, 0)
        self._redis.xadd(stream_key, {"cursor": str(cursor), "event": json.dumps(asdict(stored), ensure_ascii=True)}, maxlen=self._event_retention, approximate=True)
        self._redis.expire(stream_key, self._runtime_ttl_seconds)
        return stored

    def list_events_for_session(self, *, session_id):
        records = []
        for _stream_id, fields in self._redis.xrange(f"offersteady:realtime:events:{session_id}"):
            raw = fields.get("event")
            if raw:
                records.append(RealtimeEvent(**json.loads(raw)))
        return records

    def get_session_activity_version(self, *, session_id):
        items = self._redis.xrevrange(f"offersteady:realtime:events:{session_id}", count=1)
        return int(items[0][1].get("cursor", "0")) if items else 0

    def get_event_stream_version(self, *, session_id: str) -> int:
        items = self._redis.xrevrange(f"offersteady:realtime:events:{session_id}", count=1)
        if not items:
            return self.get_session_activity_version(session_id=session_id)
        return int(items[0][1].get("cursor", "0"))

    def readiness(self) -> bool:
        return bool(self._redis.ping())
