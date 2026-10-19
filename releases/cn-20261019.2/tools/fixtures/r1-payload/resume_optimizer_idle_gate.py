"""Read-only CN optimizer aggregate gate, runnable from the pre-feature image."""
import json
import psycopg
from app.core.config import Settings

MIGRATION_SHA = '7fe56ad0082323ea440640e2c7303305f38c22d1704bc04f94a123d4922705e7'
PROTECTED = ('resumeOptimizerQueuedOrRunning', 'unknownResumeOptimizerStates',
             'unfinishedResumeOptimizerUsages', 'unknownResumeOptimizerUsageStates',
             'resumeOptimizerReadFailures')


def collect_counts(settings, connect=psycopg.connect):
    counts = dict.fromkeys(PROTECTED, 0)
    try:
        with connect(settings.database_url, connect_timeout=3, options='-c default_transaction_read_only=on -c statement_timeout=3000') as connection:
            tables = connection.execute("SELECT to_regclass('cn_resume_optimizer_jobs'),to_regclass('cn_resume_optimizer_usage')").fetchone()
            journal = connection.execute("SELECT content_sha256 FROM offersteady_schema_migrations WHERE migration_name='0054_cn_resume_optimizer.sql'").fetchone()
            if tables == (None, None) and journal is None:
                return counts
            if tables is None or len(tables) != 2 or any(t is None for t in tables) or journal != (MIGRATION_SHA,):
                raise ValueError('migration_table_or_journal_mismatch')
            # Even an impossible unfinished tombstone is protected. Never
            # resolve, cancel or delete a row just to pass this release gate.
            row = connection.execute("""SELECT
              count(*) FILTER (WHERE status IN ('queued','running')),
              count(*) FILTER (WHERE status IS NULL OR status NOT IN ('queued','running','completed','failed','cancelled'))
              FROM cn_resume_optimizer_jobs""").fetchone()
            usage = connection.execute("""SELECT
              count(*) FILTER (WHERE status='reserved'),
              count(*) FILTER (WHERE status IS NULL OR status NOT IN ('reserved','settled','released'))
              FROM cn_resume_optimizer_usage""").fetchone()
            if row is None or len(row) != 2 or usage is None or len(usage) != 2 or any(type(v) is not int or v < 0 for v in (*row, *usage)):
                raise ValueError('aggregate_shape')
            counts['resumeOptimizerQueuedOrRunning'], counts['unknownResumeOptimizerStates'] = row
            counts['unfinishedResumeOptimizerUsages'], counts['unknownResumeOptimizerUsageStates'] = usage
    except Exception:
        counts['resumeOptimizerReadFailures'] = 1
    return counts


if __name__ == '__main__':
    counts = collect_counts(Settings(_env_file=None))
    print(json.dumps(counts))
    raise SystemExit(75 if any(counts.values()) else 0)
