import json
import os
import sys
import time

import psycopg
import redis

now_ms = int(time.time() * 1000)
with psycopg.connect(os.environ["OFFERSTEADY_DATABASE_URL"], connect_timeout=3,
                     options="-c default_transaction_read_only=on -c statement_timeout=3000") as connection:
    live, preparing = connection.execute(
        """SELECT count(*) FILTER (WHERE status='live'),
           count(*) FILTER (WHERE status='preparing' AND deleted_at_ms IS NULL AND updated_at_ms > %s)
           FROM interview_sessions""", (now_ms - 120000,),
    ).fetchone()
client = redis.Redis.from_url(os.environ["OFFERSTEADY_REDIS_URL"], socket_timeout=3, socket_connect_timeout=3)
samples = client.zrevrange("offersteady:admin:capacity:v1", 0, 0)
sample = json.loads(samples[0]) if samples else {}
age_ms = now_ms - int(sample.get("atMs", 0))
summary = {"atMs": now_ms, "liveInterviews": live, "recentPreparing": preparing,
           "sampleAgeMs": age_ms,
           **{key: sample.get(key) for key in ("activeInterviews", "activeWebSessions", "activeAudioStreams")}}
print(json.dumps(summary))
sys.exit(0 if live == 0 and preparing == 0 and 0 <= age_ms < 90000
         and all(summary[key] == 0 for key in ("activeInterviews", "activeWebSessions", "activeAudioStreams")) else 75)
