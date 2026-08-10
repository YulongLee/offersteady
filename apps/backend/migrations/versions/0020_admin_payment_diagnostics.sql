-- Safe, structured payment callback diagnostics for admin operations.

ALTER TABLE billing_payment_callback_events
  ADD COLUMN IF NOT EXISTS app_identity_verified BOOLEAN NULL;
ALTER TABLE billing_payment_callback_events
  ADD COLUMN IF NOT EXISTS seller_identity_verified BOOLEAN NULL;
ALTER TABLE billing_payment_callback_events
  ADD COLUMN IF NOT EXISTS order_known BOOLEAN NULL;
ALTER TABLE billing_payment_callback_events
  ADD COLUMN IF NOT EXISTS amount_matches BOOLEAN NULL;

ALTER TABLE billing_reconciliation_issues
  DROP CONSTRAINT IF EXISTS billing_reconciliation_issues_issue_type_check;
ALTER TABLE billing_reconciliation_issues
  ADD CONSTRAINT billing_reconciliation_issues_issue_type_check
  CHECK (issue_type IN (
    'unknown_order', 'amount_mismatch', 'provider_mismatch', 'processing_failure',
    'invalid_signature', 'app_identity_mismatch', 'seller_identity_mismatch'
  ));

CREATE INDEX IF NOT EXISTS idx_billing_checkout_orders_paid_at
  ON billing_checkout_orders(paid_at_ms DESC)
  WHERE status = 'paid';

CREATE INDEX IF NOT EXISTS idx_billing_callback_events_received_outcome
  ON billing_payment_callback_events(first_received_at_ms DESC, outcome);
