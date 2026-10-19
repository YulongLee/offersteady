import json
import time
from datetime import datetime, timezone

import psycopg
import redis
from app.core.config import get_settings

s = get_settings()
now = int(time.time() * 1000)
with psycopg.connect(s.database_url, connect_timeout=3, options="-c default_transaction_read_only=on -c statement_timeout=5000") as c:
    live = c.execute("SELECT count(*) FROM interview_sessions WHERE status='live' AND deleted_at_ms IS NULL").fetchone()[0]
r = redis.Redis.from_url(s.redis_url, decode_responses=True, socket_timeout=3)
snapshot = json.loads(r.get("offersteady:realtime:runtime:v2") or "{}")
heartbeats = list(snapshot.get("heartbeats", []))
heartbeats.extend(json.loads(value) for _, value in r.hscan_iter("offersteady:realtime:runtime:v2:entities:web-heartbeats:v1", count=100))
pages = {item.get("session_id") for item in heartbeats if item.get("page") == "live" and int(item.get("lease_expires_at_ms") or 0) > now}
audio = set()
for _, value in r.hscan_iter("offersteady:realtime:runtime:v2:receipts", count=100):
    item = json.loads(value)
    if int(item.get("received_at_ms") or 0) >= now - 30000 and int(item.get("frame_count") or 0) > 0 and item.get("asr_status") in {"pending", "accepted"}:
        audio.add((item.get("session_id"), item.get("source_kind"), item.get("source_id")))
tasks = 0
for prefix in ("offersteady:live:chat:v1:task:*", "offersteady:live:screenshot:v1:task:*"):
    for key in r.scan_iter(match=prefix, count=100):
        value = r.get(key)
        if value and json.loads(value).get("status") in {"queued", "running", "streaming", "processing"}:
            tasks += 1
report = {"checked_at": datetime.now(timezone.utc).isoformat(), "live_interviews": live, "live_page_leases": len(pages), "recent_audio_tracks": len(audio), "unfinished_answers": tasks}
print(json.dumps(report), flush=True)
if any((live, pages, audio, tasks)):
    raise SystemExit(12)
