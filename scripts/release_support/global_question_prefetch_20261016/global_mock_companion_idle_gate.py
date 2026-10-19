"""Run inside the Global backend: read-only counts, no user/provider content."""
import json
import sys
import time

import psycopg
from redis import Redis

from app.core.config import Settings


def main():
    settings = Settings()
    if settings.product_edition != "global" or not settings.redis_url:
        raise SystemExit(75)
    now = int(time.time() * 1000)
    counts = {}
    with psycopg.connect(settings.database_url, connect_timeout=3,
            options="-c default_transaction_read_only=on -c statement_timeout=3000") as connection:
        with connection.cursor() as cursor:
            cursor.execute("""SELECT count(*) FROM mock_interviews WHERE deleted_at_ms IS NULL AND (
                COALESCE((data->>'lease_until_ms')::bigint,0)>%s OR
                COALESCE((data->>'generation_claim_until_ms')::bigint,0)>%s)""", (now, now))
            counts["mockControlOrGenerationLeases"] = cursor.fetchone()[0]
            for table in ("material_processing_jobs", "material_deletion_jobs", "material_reconcile_jobs"):
                cursor.execute("SELECT count(*) FROM " + table + " WHERE status IN ('queued','retrying','running')")
                counts[table] = cursor.fetchone()[0]
            cursor.execute("""SELECT count(*) FROM material_processing_tasks t
                WHERE current_stage NOT IN ('COMPLETED','FAILED') AND NOT (
                    current_stage='QUEUED' AND updated_at_ms<%s AND EXISTS (
                        SELECT 1 FROM material_processing_jobs j
                        WHERE j.related_task_id=t.task_id AND j.status='failed'))""", (now-86_400_000,))
            counts["protectedMaterialTasks"] = cursor.fetchone()[0]
    redis = Redis.from_url(settings.redis_url, decode_responses=True,
        socket_timeout=3, socket_connect_timeout=3)
    # The isolated Global Redis uses the existing shared key names. Reading raw
    # hashes avoids repository constructors, migrations or task repair writes.
    prefix = "offersteady:realtime:runtime:v2"
    snapshot = json.loads(redis.get(prefix) or "{}")
    heartbeats = [json.loads(raw) for raw in redis.hvals(prefix + ":entities:web-heartbeats:v1")]
    heartbeats.extend(snapshot.get("heartbeats", []))
    active_pages = {(row.get("owner_user_id"), row.get("session_id")) for row in heartbeats
        if int(row.get("lease_expires_at_ms") or 0) > now}
    counts["activeEntityOrLegacyPageLeases"] = len(active_pages)
    print(json.dumps(counts, sort_keys=True))
    raise SystemExit(0 if all(value == 0 for value in counts.values()) else 75)


if __name__ == "__main__":
    try:
        main()
    except Exception:
        # Never emit SQL, a connection URI or malformed Redis payload on error.
        print(json.dumps({"gateReadFailed": True}))
        raise SystemExit(75) from None
