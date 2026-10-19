"""Read-only release gate. Print aggregates only, never session/user content."""
import json
import time
import psycopg
from redis import Redis
from app.core.config import Settings

settings = Settings()
assert settings.product_edition == "global", "Wrong edition"
now = int(time.time() * 1000)
with psycopg.connect(settings.database_url, connect_timeout=5) as connection:
    with connection.cursor() as cursor:
        cursor.execute("SET TRANSACTION READ ONLY")
        cursor.execute("SELECT count(*) FROM interview_sessions WHERE status = 'live' AND deleted_at_ms IS NULL")
        live = cursor.fetchone()[0]
        cursor.execute("SELECT count(*) FROM interview_sessions WHERE status = 'preparing' AND deleted_at_ms IS NULL AND updated_at_ms > %s", (now - 300_000,))
        preparing = cursor.fetchone()[0]
        cursor.execute("SELECT count(*) FROM material_processing_jobs WHERE status = 'running'")
        material_jobs = cursor.fetchone()[0]
redis = Redis.from_url(settings.redis_url, decode_responses=True, socket_timeout=5, socket_connect_timeout=5)
runtime = json.loads(redis.get("offersteady:realtime:runtime:v2") or "{}")
pages = sum(item.get("page") == "live" and int(item.get("lease_expires_at_ms") or 0) > now for item in runtime.get("heartbeats", []))
audio = { (item.get("session_id"), item.get("source_kind"), item.get("source_id"))
    for value in redis.hvals("offersteady:realtime:runtime:v2:receipts") for item in [json.loads(value)]
    if int(item.get("received_at_ms") or 0) > now - 30_000 and int(item.get("frame_count") or 0) > 0
    and item.get("asr_status") in {"pending", "accepted"} }
tasks = 0
for pattern in ("offersteady:live:chat:v1:task:*", "offersteady:live:screenshot:v1:task:*", "offersteady:live:screenshot:v1:request:*"):
    for key in redis.scan_iter(match=pattern, count=100):
        if key.endswith(":lock"):
            continue
        raw = redis.get(key)
        if raw:
            item = json.loads(raw)
            tasks += item.get("status") not in {"completed", "failed", "cancelled", "expired"}
counts = {"atMs": now, "liveInterviews": live, "recentPreparing": preparing, "livePageLeases": pages, "recentAudioTracks": len(audio), "unfinishedTasks": tasks, "runningMaterialJobs": material_jobs}
print(json.dumps(counts))
raise SystemExit(0 if live == preparing == pages == len(audio) == tasks == material_jobs == 0 else 20)
