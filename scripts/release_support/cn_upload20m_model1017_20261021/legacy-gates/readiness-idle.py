"""Read-only mock gate; preparing may reconnect, live practice may not switch."""
import json
import time
import psycopg
from app.core.config import get_settings

s = get_settings()
with psycopg.connect(s.database_url, connect_timeout=3,
        options='-c default_transaction_read_only=on -c statement_timeout=3000') as conn:
    rows = conn.execute("""SELECT data->'state'->>'phase', count(*)
        FROM mock_interviews WHERE deleted_at_ms IS NULL GROUP BY 1""").fetchall()
summary = dict(rows)
print(json.dumps({'mockPhases': summary}))
assert all(phase in ('preparing', 'completed') or count == 0 for phase, count in rows), 'mock practice active'
