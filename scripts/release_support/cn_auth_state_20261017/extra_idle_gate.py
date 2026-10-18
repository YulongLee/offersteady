"""Read-only supplement to the reviewed CN deployment gates; print counts only."""
from __future__ import annotations

import json
import time

import psycopg
import redis


SQL = """SELECT
 count(*) FILTER (WHERE data->'state'->>'phase'='preparing' AND updated_at_ms > %s),
 count(*) FILTER (WHERE data->'state'->>'phase'='preparing' AND COALESCE((data->>'lease_until_ms')::bigint,0) >= %s),
 count(*) FILTER (WHERE data->'state'->>'phase'='preparing' AND (
   updated_at_ms > %s OR COALESCE((data->>'lease_until_ms')::bigint,0) >= %s)),
 count(*) FILTER (WHERE data->'state'->>'phase'='preparing' AND (
   updated_at_ms <= %s AND COALESCE((data->>'lease_until_ms')::bigint,0) < %s)),
 count(*) FILTER (WHERE data->'state'->>'phase'='generating_question'),
 count(*) FILTER (WHERE data->'state'->>'phase'='speaking'),
 count(*) FILTER (WHERE data->'state'->>'phase'='listening'),
 count(*) FILTER (WHERE data->'state'->>'phase'='paused'),
 count(*) FILTER (WHERE data->'state'->>'phase'='generating_report'),
 count(*) FILTER (WHERE data->'state'->>'phase' IS NULL OR data->'state'->>'phase' NOT IN
   ('preparing','generating_question','speaking','listening','paused','generating_report','completed')),
 count(*) FILTER (WHERE data->>'generation_claim' IS NOT NULL
   AND COALESCE((data->>'generation_claim_until_ms')::bigint,0) >= %s)
 FROM mock_interviews WHERE deleted_at_ms IS NULL"""
MOCK_FIELDS = (
    "mockPreparingRecent120Seconds", "mockPreparingLeased", "mockPreparingProtected",
    "mockOldPreparingWithoutLease", "mockGeneratingQuestion", "mockSpeaking", "mockListening",
    "mockPaused", "mockGeneratingReport", "mockUnknownPhase", "mockEffectiveGenerationClaims",
)
PROTECTED = (
    "mockPreparingProtected", "mockGeneratingQuestion", "mockSpeaking", "mockListening",
    "mockPaused", "mockGeneratingReport", "mockUnknownPhase", "mockEffectiveGenerationClaims",
    "livePageLeases", "preparationPageLeases", "unknownPageLeases", "unfinishedChatTasks",
    "unfinishedScreenshotTasks", "unknownChatTaskStatuses", "unknownScreenshotTaskStatuses",
    "invalidRuntimeMetadata", "metadataReadFailures",
)
TERMINAL = frozenset({"completed", "failed", "cancelled"})
TASKS = (
    ("offersteady:live:chat:v1:task:*", "Chat", TERMINAL | {"queued", "streaming"}),
    ("offersteady:live:screenshot:v1:task:*", "Screenshot",
     TERMINAL | {"queued", "processing-images", "vision-running", "streaming"}),
)


def collect_counts(settings, *, now_ms, connect=psycopg.connect, redis_factory=redis.Redis.from_url):
    counts = {field: 0 for field in (*MOCK_FIELDS, *PROTECTED)}
    with connect(settings.database_url, connect_timeout=3,
                 options="-c default_transaction_read_only=on -c statement_timeout=3000") as connection:
        row = connection.execute(SQL, (now_ms-120000, now_ms, now_ms-120000, now_ms,
                                       now_ms-120000, now_ms, now_ms)).fetchone()
    counts.update(zip(MOCK_FIELDS, row))
    client = redis_factory(settings.redis_url, decode_responses=True,
                           socket_timeout=3, socket_connect_timeout=3)

    def decode(raw):
        try:
            value = json.loads(raw)
            if not isinstance(value, dict):
                raise ValueError("metadata shape")
            return value
        except (ValueError, TypeError):
            counts["invalidRuntimeMetadata"] += 1
            return None

    raw = client.get("offersteady:realtime:runtime:v2")
    payload = decode(raw) if raw else {}
    heartbeats = payload.get("heartbeats", []) if payload is not None else []
    if not isinstance(heartbeats, list):
        counts["invalidRuntimeMetadata"] += 1
        heartbeats = []
    for _, raw in client.hscan_iter("offersteady:realtime:runtime:v2:entities:web-heartbeats:v1", count=100):
        record = decode(raw)
        if record is not None:
            heartbeats.append(record)
    leases = {}
    for item in heartbeats:
        try:
            if not isinstance(item, dict):
                raise ValueError("heartbeat shape")
            if int(item.get("lease_expires_at_ms") or 0) < now_ms:
                continue
            key = (item.get("session_id"), item.get("page_instance_id"), item.get("page"))
            leases[key] = item.get("page")
        except (ValueError, TypeError):
            counts["invalidRuntimeMetadata"] += 1
    for page in leases.values():
        field = "livePageLeases" if page == "live" else (
            "preparationPageLeases" if page == "preparation" else "unknownPageLeases")
        counts[field] += 1
    for pattern, kind, allowed in TASKS:
        for key in client.scan_iter(match=pattern, count=100):
            raw = client.get(key)
            if not raw:
                continue
            task = decode(raw)
            if task is None:
                continue
            status = task.get("status")
            if not isinstance(status, str) or status not in allowed:
                counts[f"unknown{kind}TaskStatuses"] += 1
            elif status not in TERMINAL:
                counts[f"unfinished{kind}Tasks"] += 1
    return counts


def blocked(counts):
    return any(counts.get(field, 0) for field in PROTECTED)


def main():
    try:
        from app.core.config import get_settings
        counts = collect_counts(get_settings(), now_ms=int(time.time()*1000))
    except Exception:
        # Never expose connection strings, Redis keys, user metadata or raw errors.
        counts = {"metadataReadFailures": 1}
    print(json.dumps(counts), flush=True)
    raise SystemExit(75 if blocked(counts) else 0)


if __name__ == "__main__":
    main()
