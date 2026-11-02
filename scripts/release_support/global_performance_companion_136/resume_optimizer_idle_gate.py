"""Read-only Global optimizer gate. Report aggregates; never reap or settle work.

The pinned release already has both optimizer tables. Missing schema is unknown,
not evidence that no work exists. Claims/leases and quota reservations are checked
independently of lifecycle/deletion fields. There is no age-based exemption.
"""
import json
import time

import psycopg
from app.core.config import Settings


PROTECTED = (
    'resumeOptimizerQueuedOrRunning', 'resumeOptimizerEffectiveClaims',
    'resumeOptimizerEffectiveLeases', 'reservedResumeOptimizerUsage',
    'unknownResumeOptimizerStates', 'unknownResumeOptimizerUsageStates',
    'invalidResumeOptimizerMetadata', 'resumeOptimizerReadFailures',
)
JOBS_SQL = """SELECT
 count(*) FILTER (WHERE status IN ('queued','running')),
 count(*) FILTER (WHERE claim_token IS NOT NULL AND lease_until_ms >= %s),
 count(*) FILTER (WHERE lease_until_ms >= %s),
 count(*) FILTER (WHERE status IS NULL OR status NOT IN ('queued','running','completed','failed','cancelled')),
 count(*) FILTER (WHERE created_at_ms IS NULL OR created_at_ms <= 0 OR
   updated_at_ms IS NULL OR updated_at_ms < created_at_ms OR updated_at_ms > %s OR
   ((claim_token IS NULL) <> (lease_until_ms IS NULL)) OR
   (claim_token IS NOT NULL AND length(btrim(claim_token))=0) OR
   (lease_until_ms IS NOT NULL AND (lease_until_ms <= 0 OR lease_until_ms < created_at_ms)))
 FROM global_resume_optimizer_jobs"""
USAGE_SQL = """SELECT
 count(*) FILTER (WHERE u.status='reserved'),
 count(*) FILTER (WHERE u.status IS NULL OR u.status NOT IN ('reserved','settled','released')),
 count(*) FILTER (WHERE j.job_id IS NULL OR u.owner_user_id IS DISTINCT FROM j.owner_user_id OR
   u.quota_day IS DISTINCT FROM j.quota_day OR u.created_at_ms IS NULL OR u.created_at_ms <= 0 OR
   u.created_at_ms > %s OR
   (u.status='reserved' AND u.finalized_at_ms IS NOT NULL) OR
   (u.status IN ('settled','released') AND (u.finalized_at_ms IS NULL OR
     u.finalized_at_ms < u.created_at_ms OR u.finalized_at_ms > %s)))
 FROM global_resume_optimizer_usage u
 LEFT JOIN global_resume_optimizer_jobs j ON j.job_id=u.job_id"""


def aggregate(row, size):
    if row is None or len(row) != size or any(type(value) is not int or value < 0 for value in row):
        raise ValueError('aggregate_shape')
    return row


def collect_counts(settings, *, now_ms, connect=psycopg.connect):
    counts = dict.fromkeys(PROTECTED, 0)
    try:
        if settings.product_edition != 'global' or settings.environment != 'production':
            raise ValueError('wrong_edition')
        if type(now_ms) is not int or now_ms <= 0:
            raise ValueError('invalid_time')
        with connect(settings.database_url, connect_timeout=3,
                     options='-c default_transaction_read_only=on -c statement_timeout=3000') as connection:
            jobs = aggregate(connection.execute(JOBS_SQL, (now_ms, now_ms, now_ms + 5_000)).fetchone(), 5)
            usage = aggregate(connection.execute(USAGE_SQL, (now_ms + 5_000, now_ms + 5_000)).fetchone(), 3)
        counts.update(resumeOptimizerQueuedOrRunning=jobs[0],
                      resumeOptimizerEffectiveClaims=jobs[1], resumeOptimizerEffectiveLeases=jobs[2],
                      reservedResumeOptimizerUsage=usage[0], unknownResumeOptimizerStates=jobs[3],
                      unknownResumeOptimizerUsageStates=usage[1], invalidResumeOptimizerMetadata=jobs[4]+usage[2])
    except Exception:
        counts['resumeOptimizerReadFailures'] = 1
    return counts


def blocked(counts):
    return set(counts) != set(PROTECTED) or any(type(counts.get(field)) is not int or counts[field] != 0 for field in PROTECTED)


if __name__ == '__main__':
    try:
        result = collect_counts(Settings(_env_file=None), now_ms=int(time.time()*1000))
    except Exception:
        result = dict.fromkeys(PROTECTED, 0)
        result['resumeOptimizerReadFailures'] = 1
    print(json.dumps(result))
    raise SystemExit(75 if blocked(result) else 0)
