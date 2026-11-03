"""Read-only Global supplement to reviewed legacy and lease/task gates.

Print fixed aggregate counts only. Never instantiate business repositories,
initialize schemas, resolve stale work or mutate Redis/database records.
"""
from __future__ import annotations

import json
import time

import psycopg
import redis


SNAPSHOT = "offersteady:realtime:runtime:v2"
PUBLISHERS = SNAPSHOT + ":publishers"
RECEIPTS = SNAPSHOT + ":receipts"
CAPTURE_REQUESTS = "offersteady:live:screenshot:v1:request:*"
MAX_RECORDS = 20_000
PUBLISHER_ACTIVE = frozenset({
    "connected", "receiving-audio", "transcribing", "degraded", "reconnecting", "answer-streaming",
})
PUBLISHER_TERMINAL = frozenset({"closed", "failed"})
CAPTURE_ACTIVE = frozenset({"requested", "processing"})
CAPTURE_TERMINAL = frozenset({"completed", "failed", "cancelled"})
MATERIAL_TABLES = (
    ("material_processing_jobs", "materialProcessingJobs"),
    ("material_deletion_jobs", "materialDeletionJobs"),
    ("material_reconcile_jobs", "materialReconcileJobs"),
)
MATERIAL_JOB_SQL = """SELECT
 count(*) FILTER (WHERE status IN ('queued','retrying','running')),
 count(*) FILTER (WHERE status IS NULL OR status NOT IN
  ('queued','retrying','running','succeeded','failed','cancelled')) FROM {}"""
MATERIAL_TASK_SQL = """SELECT
 count(*) FILTER (WHERE current_stage IS NULL OR (current_stage NOT IN ('COMPLETED','FAILED')
  AND NOT COALESCE(current_stage='QUEUED' AND updated_at_ms < %s AND EXISTS (
   SELECT 1 FROM material_processing_jobs j
   WHERE j.related_task_id=t.task_id AND j.status='failed'),false))),
 count(*) FILTER (WHERE current_stage='QUEUED' AND updated_at_ms < %s AND EXISTS (
  SELECT 1 FROM material_processing_jobs j
  WHERE j.related_task_id=t.task_id AND j.status='failed'))
 FROM material_processing_tasks t"""
PROTECTED = (
    "connectedDesktopPublishers", "workingDesktopPublishers", "availablePublisherTokens", "unknownPublisherStatuses",
    "recentAudioTracks", "unfinishedRemoteCaptures", "unknownRemoteCaptureStatuses",
    "materialProcessingJobs", "materialDeletionJobs", "materialReconcileJobs",
    "unknownMaterialJobStatuses", "activeMaterialTasks", "invalidRuntimeMetadata",
    "metadataReadFailures", "scanLimitExceeded",
)


def collect_counts(settings, *, now_ms, connect=psycopg.connect, redis_factory=redis.Redis.from_url):
    counts = dict.fromkeys((*PROTECTED, "ignoredLegacyFailedQueuedTasks"), 0)
    with connect(settings.database_url, connect_timeout=3,
                 options="-c default_transaction_read_only=on -c statement_timeout=3000") as connection:
        for table, field in MATERIAL_TABLES:
            row = connection.execute(MATERIAL_JOB_SQL.format(table)).fetchone()
            if row is None or len(row) != 2 or any(type(item) is not int or item < 0 for item in row):
                raise ValueError("aggregate shape")
            counts[field] = row[0]
            counts["unknownMaterialJobStatuses"] += row[1]
        cutoff = now_ms - 86_400_000
        row = connection.execute(MATERIAL_TASK_SQL, (cutoff, cutoff)).fetchone()
        if row is None or len(row) != 2 or any(type(item) is not int or item < 0 for item in row):
            raise ValueError("aggregate shape")
        counts["activeMaterialTasks"], counts["ignoredLegacyFailedQueuedTasks"] = row

    client = redis_factory(settings.redis_url, decode_responses=True,
                           socket_timeout=3, socket_connect_timeout=3)
    seen = 0

    def decode(raw):
        nonlocal seen
        seen += 1
        if seen > MAX_RECORDS:
            counts["scanLimitExceeded"] += 1
            raise ValueError("scan limit")
        try:
            value = json.loads(raw)
            if not isinstance(value, dict):
                raise ValueError("metadata shape")
            return value
        except (ValueError, TypeError):
            counts["invalidRuntimeMetadata"] += 1
            return None

    def timestamp(value):
        if type(value) is not int or value < 0:
            raise ValueError("timestamp shape")
        return value

    try:
        raw = client.get(SNAPSHOT)
        payload = decode(raw) if raw is not None else {}
        payload = payload or {}
        publishers = {}
        for field in ("publishers", "receipts"):
            if not isinstance(payload.get(field, []), list):
                counts["invalidRuntimeMetadata"] += 1
                payload[field] = []
        for item in payload.get("publishers", []):
            item = decode(json.dumps(item))
            if item is not None:
                publishers[item.get("publisher_id")] = item
        # The entity hash is authoritative over a duplicate legacy snapshot.
        for _, value in client.hscan_iter(PUBLISHERS, count=100):
            item = decode(value)
            if item is not None:
                publishers[item.get("publisher_id")] = item
        for publisher_id, item in publishers.items():
            try:
                if not isinstance(publisher_id, str) or not publisher_id or not isinstance(item.get("session_id"), str):
                    raise ValueError("publisher identity")
                status = item.get("status")
                if not isinstance(status, str) or status not in PUBLISHER_ACTIVE | PUBLISHER_TERMINAL:
                    counts["unknownPublisherStatuses"] += 1
                    continue
                expiry = timestamp(item.get("expires_at_ms"))
                connected = item.get("connected_at_ms")
                disconnected = item.get("disconnected_at_ms")
                if connected is not None:
                    timestamp(connected)
                if disconnected is not None:
                    timestamp(disconnected)
                if status in PUBLISHER_TERMINAL:
                    continue
                # Expiry controls connecting, not an already-open WebSocket.
                if connected is not None and disconnected is None:
                    counts["connectedDesktopPublishers"] += 1
                elif status != "connected":
                    # Legacy HTTP uploaders need not set connected_at_ms before
                    # entering a working/recovery state. Do not treat their
                    # expired connection token as proof of inactivity.
                    counts["workingDesktopPublishers"] += 1
                elif expiry >= now_ms:
                    counts["availablePublisherTokens"] += 1
            except (ValueError, TypeError):
                counts["invalidRuntimeMetadata"] += 1
        audio = set()

        def observe_receipt(item):
            try:
                status = item.get("asr_status")
                if status not in {"pending", "accepted", "failed"}:
                    raise ValueError("receipt status")
                received = timestamp(item.get("received_at_ms"))
                frames = timestamp(item.get("frame_count"))
                if received >= now_ms - 30_000 and frames > 0 and status in {"pending", "accepted"}:
                    identity = tuple(item.get(field) for field in ("session_id", "source_kind", "source_id"))
                    if not all(isinstance(value, str) and value for value in identity):
                        raise ValueError("receipt identity")
                    audio.add(identity)
            except (ValueError, TypeError):
                counts["invalidRuntimeMetadata"] += 1

        for value in payload.get("receipts", []):
            item = decode(json.dumps(value))
            if item is not None:
                observe_receipt(item)
        for _, value in client.hscan_iter(RECEIPTS, count=100):
            item = decode(value)
            if item is not None:
                observe_receipt(item)
        counts["recentAudioTracks"] = len(audio)
        for key in client.scan_iter(match=CAPTURE_REQUESTS, count=100):
            raw = client.get(key)
            if raw is None:  # A normal TTL expiry between SCAN and GET.
                continue
            item = decode(raw)
            if item is None:
                continue
            status = item.get("status")
            if not isinstance(status, str) or status not in CAPTURE_ACTIVE | CAPTURE_TERMINAL:
                counts["unknownRemoteCaptureStatuses"] += 1
            elif status in CAPTURE_ACTIVE:
                counts["unfinishedRemoteCaptures"] += 1
        return counts
    finally:
        client.close()


def blocked(counts):
    return any(type(counts.get(field)) is not int or counts[field] != 0 for field in PROTECTED)


def main():
    try:
        from app.core.config import get_settings
        settings = get_settings()
        if settings.product_edition != "global" or settings.environment != "production":
            raise ValueError("wrong release edition")
        counts = collect_counts(settings, now_ms=int(time.time() * 1000))
    except Exception:
        # Fail closed without printing credentials, keys, user data or errors.
        counts = {"metadataReadFailures": 1}
    print(json.dumps(counts), flush=True)
    raise SystemExit(75 if blocked(counts) else 0)


if __name__ == "__main__":
    main()
