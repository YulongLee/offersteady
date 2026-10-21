"""Read-only, aggregate-only gate for still-active financial operations.

Stale expired/unpaid orders do not prevent release indefinitely. An order with
an unexpired payment action or an unfinished callback received in the last two
minutes is protected; no order/callback is resolved, expired or altered here.
"""
import json
import os
import time
import psycopg
from app.core.config import Settings

PROTECTED = ('pendingValidCheckoutOrders', 'recentUnfinishedPaymentCallbacks',
             'unknownCheckoutStates', 'financialReadFailures', 'unfinishedUsageReservations', 'unknownUsageReservationStates', 'unfinishedIndexReservations', 'unknownIndexReservationStates')
INFORMATIONAL = ('historicalOrphanAnswerReservations',)

# Answers execute only inside the Backend process. A surviving expired
# reservation from before the pinned original process was born cannot be that
# process's running answer. A replay first executes the existing per-user TTL
# release before looking up the reservation. This is an inventory classification,
# never a balance/status write. Every other protected-work gate remains required.
USAGE_SQL = """SELECT
 count(*) FILTER (WHERE status='reserved' AND NOT COALESCE(
   usage_kind='answer' AND created_at_ms>0 AND created_at_ms<%s AND created_at_ms<%s,false)),
 count(*) FILTER (WHERE status IS NULL OR status NOT IN
   ('reserved','settled','released','insufficient_balance')),
 count(*) FILTER (WHERE status='reserved' AND COALESCE(
   usage_kind='answer' AND created_at_ms>0 AND created_at_ms<%s AND created_at_ms<%s,false))
 FROM billing_usage_reservations"""


def collect_counts(settings, *, now_ms, orphan_before_process_ms=None, connect=psycopg.connect):
    counts = dict.fromkeys((*PROTECTED, *INFORMATIONAL), 0)
    try:
        if type(now_ms) is not int or type(orphan_before_process_ms) is not int or not 0<orphan_before_process_ms<=now_ms:
            raise ValueError('missing_or_invalid_original_process_anchor')
        # Match the application's effective TTL, including its lower bound.
        ttl_seconds=max(60,int(settings.billing_usage_reservation_ttl_seconds))
        expired_before=now_ms-ttl_seconds*1000
        with connect(settings.database_url, connect_timeout=3,
                     options='-c default_transaction_read_only=on -c statement_timeout=3000') as connection:
            usage=connection.execute(USAGE_SQL,(expired_before,orphan_before_process_ms,expired_before,orphan_before_process_ms)).fetchone()
            if not usage or len(usage)!=3 or any(type(v) is not int or v<0 for v in usage):
                raise ValueError('usage_reservation_aggregate_shape')
            counts['unfinishedUsageReservations'],counts['unknownUsageReservationStates'],counts['historicalOrphanAnswerReservations']=usage
            for table, field, unknown in (('billing_index_reservations','unfinishedIndexReservations','unknownIndexReservationStates'),):
                reservation=connection.execute("SELECT count(*) FILTER (WHERE status='reserved'),count(*) FILTER (WHERE status IS NULL OR status NOT IN ('reserved','settled','released','insufficient_balance')) FROM "+table).fetchone()
                if not reservation or len(reservation)!=2 or any(type(v) is not int or v<0 for v in reservation):
                    raise ValueError('reservation_aggregate_shape')
                counts[field],counts[unknown]=reservation
            row = connection.execute("""SELECT
                count(*) FILTER (WHERE status='payment_pending' AND expires_at_ms >= %s),
                count(*) FILTER (WHERE status IS NULL OR status NOT IN ('payment_pending','paid','expired','failed'))
                FROM billing_checkout_orders""", (now_ms,)).fetchone()
            callbacks = connection.execute("""SELECT count(*) FROM billing_payment_callback_events
                WHERE completed_at_ms IS NULL AND last_received_at_ms >= %s""", (now_ms - 120_000,)).fetchone()
            if row is None or len(row) != 2 or callbacks is None or len(callbacks) != 1 or any(type(v) is not int or v < 0 for v in (*row, *callbacks)):
                raise ValueError('aggregate_shape')
            counts['pendingValidCheckoutOrders'], counts['unknownCheckoutStates'] = row
            counts['recentUnfinishedPaymentCallbacks'] = callbacks[0]
    except Exception:
        counts['financialReadFailures'] = 1
    return counts


if __name__ == '__main__':
    try:
        raw=os.environ.get('OFFERSTEADY_RELEASE_ORIGINAL_BACKEND_STARTED_AT_MS','')
        anchor=int(raw) if raw.isdigit() else None
    except (TypeError,ValueError):
        anchor=None
    counts = collect_counts(Settings(_env_file=None), now_ms=int(time.time() * 1000),orphan_before_process_ms=anchor)
    print(json.dumps(counts))
    raise SystemExit(75 if any(counts[field] for field in PROTECTED) else 0)
