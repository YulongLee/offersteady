"""Read-only Global commerce gate; never resolve orders or change entitlements.

Keep Global checkout/callback semantics and protect every unfinished entitlement
reservation. Global has no CN reservation TTL/orphan exception. Unknown data or
schema fails closed; output contains fixed aggregate counts only.
"""
import json
import time

import psycopg
from app.core.config import Settings


PROTECTED = (
    'recentCommerceCheckouts', 'processingProviderEvents',
    'unfinishedCommerceUsageReservations', 'unknownCommerceStates',
    'unknownCommerceUsageStates', 'invalidFinancialMetadata',
    'invalidCommerceUsageMetadata', 'financialReadFailures',
)
ORDERS_SQL = """SELECT
 count(*) FILTER (WHERE status IN ('pending','checkout_created','confirming') AND updated_at_ms >= %s),
 count(*) FILTER (WHERE status IS NULL OR status NOT IN
   ('pending','checkout_created','confirming','paid','failed','expired','refunded','disputed')),
 count(*) FILTER (WHERE created_at_ms IS NULL OR updated_at_ms IS NULL OR
   created_at_ms <= 0 OR updated_at_ms < created_at_ms OR updated_at_ms > %s)
 FROM global_commerce_orders"""
EVENTS_SQL = """SELECT
 count(*) FILTER (WHERE status='processing'),
 count(*) FILTER (WHERE status IS NULL OR status NOT IN ('processing','processed','ignored','failed')),
 count(*) FILTER (WHERE received_at_ms IS NULL OR received_at_ms <= 0 OR received_at_ms > %s)
 FROM global_commerce_provider_events"""
USAGE_SQL = """SELECT
 count(*) FILTER (WHERE status='reserved'),
 count(*) FILTER (WHERE status IS NULL OR status NOT IN ('reserved','settled','released') OR
   usage_kind IS NULL OR usage_kind NOT IN ('copilot_minute','screen_assist','knowledge_token')),
 count(*) FILTER (WHERE created_at_ms IS NULL OR created_at_ms <= 0 OR created_at_ms > %s OR
   amount IS NULL OR amount <= 0 OR
   (status='reserved' AND (settled_at_ms IS NOT NULL OR released_at_ms IS NOT NULL)) OR
   (status='settled' AND (settled_at_ms IS NULL OR settled_at_ms < created_at_ms OR
     settled_at_ms > %s OR released_at_ms IS NOT NULL)) OR
   (status='released' AND (released_at_ms IS NULL OR released_at_ms < created_at_ms OR
     released_at_ms > %s OR settled_at_ms IS NOT NULL)))
 FROM global_commerce_usage_reservations"""


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
            orders = aggregate(connection.execute(ORDERS_SQL, (now_ms-120_000, now_ms+5_000)).fetchone(), 3)
            events = aggregate(connection.execute(EVENTS_SQL, (now_ms+5_000,)).fetchone(), 3)
            usage = aggregate(connection.execute(USAGE_SQL, (now_ms+5_000, now_ms+5_000, now_ms+5_000)).fetchone(), 3)
        counts.update(recentCommerceCheckouts=orders[0], processingProviderEvents=events[0],
                      unfinishedCommerceUsageReservations=usage[0], unknownCommerceStates=orders[1]+events[1],
                      unknownCommerceUsageStates=usage[1], invalidFinancialMetadata=orders[2]+events[2],
                      invalidCommerceUsageMetadata=usage[2])
    except Exception:
        counts['financialReadFailures'] = 1
    return counts


def blocked(counts):
    return set(counts) != set(PROTECTED) or any(type(counts.get(field)) is not int or counts[field] != 0 for field in PROTECTED)


if __name__ == '__main__':
    try:
        result = collect_counts(Settings(_env_file=None), now_ms=int(time.time()*1000))
    except Exception:
        result = dict.fromkeys(PROTECTED, 0)
        result['financialReadFailures'] = 1
    print(json.dumps(result))
    raise SystemExit(75 if blocked(result) else 0)
