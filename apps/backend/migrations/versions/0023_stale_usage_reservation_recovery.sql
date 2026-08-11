-- Release abandoned answer/screenshot reservations and keep future recovery bounded.

CREATE INDEX IF NOT EXISTS idx_billing_usage_reservations_status_created
  ON billing_usage_reservations(status, created_at_ms);

UPDATE billing_usage_reservations
SET status = 'released',
    released_at_ms = (EXTRACT(EPOCH FROM clock_timestamp()) * 1000)::BIGINT
WHERE status = 'reserved'
  AND created_at_ms < (EXTRACT(EPOCH FROM clock_timestamp()) * 1000)::BIGINT - 1800000;
