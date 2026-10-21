"""Read-only, aggregate-only gate for still-active financial operations.

Stale expired/unpaid orders do not prevent release indefinitely. An order with
an unexpired payment action or an unfinished callback received in the last two
minutes is protected; no order/callback is resolved, expired or altered here.
"""
import json
import time
import psycopg
from app.core.config import Settings

PROTECTED = ('pendingValidCheckoutOrders', 'recentUnfinishedPaymentCallbacks',
             'unknownCheckoutStates', 'financialReadFailures', 'unfinishedUsageReservations', 'unknownUsageReservationStates', 'unfinishedIndexReservations', 'unknownIndexReservationStates')


def collect_counts(settings, *, now_ms, connect=psycopg.connect):
    counts = dict.fromkeys(PROTECTED, 0)
    try:
        with connect(settings.database_url, connect_timeout=3,
                     options='-c default_transaction_read_only=on -c statement_timeout=3000') as connection:
            for table, field, unknown in (('billing_usage_reservations','unfinishedUsageReservations','unknownUsageReservationStates'),('billing_index_reservations','unfinishedIndexReservations','unknownIndexReservationStates')):
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
    counts = collect_counts(Settings(_env_file=None), now_ms=int(time.time() * 1000))
    print(json.dumps(counts))
    raise SystemExit(75 if any(counts.values()) else 0)
