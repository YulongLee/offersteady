-- Payment callback audit, checkout expiry, and reconciliation exceptions.

ALTER TABLE billing_checkout_orders
  DROP CONSTRAINT IF EXISTS billing_checkout_orders_status_check;
ALTER TABLE billing_checkout_orders
  ADD CONSTRAINT billing_checkout_orders_status_check
  CHECK (status IN ('payment_pending', 'expired', 'paid', 'failed'));

ALTER TABLE billing_checkout_orders
  ADD COLUMN IF NOT EXISTS expires_at_ms BIGINT;
ALTER TABLE billing_checkout_orders
  ADD COLUMN IF NOT EXISTS failure_reason TEXT NULL;
ALTER TABLE billing_checkout_orders
  ADD COLUMN IF NOT EXISTS last_callback_at_ms BIGINT NULL;

UPDATE billing_checkout_orders
SET expires_at_ms = CASE
  WHEN COALESCE(action->>'expiresAtMs', '') ~ '^[0-9]+$' THEN (action->>'expiresAtMs')::BIGINT
  ELSE created_at_ms + 900000
END
WHERE expires_at_ms IS NULL;

ALTER TABLE billing_checkout_orders
  ALTER COLUMN expires_at_ms SET NOT NULL;

CREATE INDEX IF NOT EXISTS idx_billing_checkout_orders_status_expiry
  ON billing_checkout_orders(status, expires_at_ms);

CREATE TABLE IF NOT EXISTS billing_payment_callback_events (
  event_fingerprint TEXT PRIMARY KEY,
  provider TEXT NOT NULL,
  order_id TEXT NOT NULL,
  provider_trade_no TEXT NULL,
  amount_cents INTEGER NOT NULL CHECK (amount_cents >= 0),
  signature_verified BOOLEAN NOT NULL,
  paid BOOLEAN NOT NULL,
  outcome TEXT NOT NULL,
  delivery_count INTEGER NOT NULL DEFAULT 1 CHECK (delivery_count > 0),
  first_received_at_ms BIGINT NOT NULL,
  last_received_at_ms BIGINT NOT NULL,
  completed_at_ms BIGINT NULL
);

CREATE INDEX IF NOT EXISTS idx_billing_callback_events_order
  ON billing_payment_callback_events(order_id, first_received_at_ms DESC);
CREATE INDEX IF NOT EXISTS idx_billing_callback_events_outcome
  ON billing_payment_callback_events(outcome, last_received_at_ms DESC);

CREATE TABLE IF NOT EXISTS billing_reconciliation_issues (
  issue_id TEXT PRIMARY KEY,
  issue_type TEXT NOT NULL CHECK (issue_type IN ('unknown_order', 'amount_mismatch', 'processing_failure')),
  event_fingerprint TEXT NOT NULL REFERENCES billing_payment_callback_events(event_fingerprint),
  order_id TEXT NOT NULL,
  safe_reference TEXT NOT NULL,
  status TEXT NOT NULL DEFAULT 'open' CHECK (status IN ('open', 'resolved')),
  detected_at_ms BIGINT NOT NULL,
  resolved_at_ms BIGINT NULL,
  UNIQUE(issue_type, event_fingerprint)
);

CREATE INDEX IF NOT EXISTS idx_billing_reconciliation_issues_status
  ON billing_reconciliation_issues(status, detected_at_ms DESC);

