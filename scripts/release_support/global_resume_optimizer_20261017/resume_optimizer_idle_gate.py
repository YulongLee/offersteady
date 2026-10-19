"""Read-only aggregate gate, also runnable in the frozen pre-feature image."""
import json
import psycopg
from app.core.config import Settings


def collect_counts(settings, connect=psycopg.connect):
    counts = {"resumeOptimizerQueuedOrRunning": 0, "unknownResumeOptimizerStates": 0, "resumeOptimizerReadFailures": 0}
    try:
        with connect(settings.database_url, connect_timeout=3, options="-c default_transaction_read_only=on -c statement_timeout=3000") as connection:
            table = connection.execute("SELECT to_regclass('global_resume_optimizer_jobs')").fetchone()
            if table is None:
                raise ValueError("aggregate_shape")
            if table[0] is None:
                applied = connection.execute("SELECT count(*) FROM offersteady_schema_migrations WHERE migration_name='0053_global_resume_optimizer.sql'").fetchone()
                if not applied or applied[0] != 0:
                    raise ValueError("applied_schema_missing")
                return counts
            row = connection.execute("""SELECT
              count(*) FILTER (WHERE status IN ('queued','running')),
              count(*) FILTER (WHERE status IS NULL OR status NOT IN ('queued','running','completed','failed','cancelled'))
              FROM global_resume_optimizer_jobs WHERE deleted_at_ms IS NULL""").fetchone()
            if row is None or len(row) != 2 or any(type(v) is not int or v < 0 for v in row):
                raise ValueError("aggregate_shape")
            counts["resumeOptimizerQueuedOrRunning"], counts["unknownResumeOptimizerStates"] = row
    except Exception:
        counts["resumeOptimizerReadFailures"] = 1
    return counts


if __name__ == "__main__":
    counts = collect_counts(Settings(_env_file=None))
    print(json.dumps(counts))
    raise SystemExit(1 if any(counts.values()) else 0)
