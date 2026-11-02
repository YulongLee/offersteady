"""Additional read-only mock interview gate; counts only."""
import json
import time
import psycopg
from app.core.config import Settings
settings = Settings()
assert settings.product_edition == 'global'
with psycopg.connect(settings.database_url, connect_timeout=5) as connection:
    with connection.cursor() as cursor:
        cursor.execute('SET TRANSACTION READ ONLY')
        cursor.execute("""SELECT count(*) FROM mock_interviews WHERE deleted_at_ms IS NULL
          AND (data->'state'->>'phase' NOT IN ('preparing','completed')
            OR (data->'state'->>'phase'='preparing' AND updated_at_ms>%s))""", (int(time.time()*1000)-300_000,))
        count = cursor.fetchone()[0]
print(json.dumps({'activeOrRecentMockInterviews':count}))
raise SystemExit(0 if count == 0 else 20)
