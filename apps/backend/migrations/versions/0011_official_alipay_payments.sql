-- Preserve the payment platform used for each order and isolate provider callbacks.

ALTER TABLE billing_checkout_orders
  ADD COLUMN IF NOT EXISTS provider TEXT;

UPDATE billing_checkout_orders
SET provider = 'mzfpay'
WHERE provider IS NULL;

ALTER TABLE billing_checkout_orders
  ALTER COLUMN provider SET NOT NULL;

ALTER TABLE billing_checkout_orders
  DROP CONSTRAINT IF EXISTS billing_checkout_orders_provider_check;
ALTER TABLE billing_checkout_orders
  ADD CONSTRAINT billing_checkout_orders_provider_check
  CHECK (provider IN ('mzfpay', 'alipay'));

ALTER TABLE billing_reconciliation_issues
  DROP CONSTRAINT IF EXISTS billing_reconciliation_issues_issue_type_check;
ALTER TABLE billing_reconciliation_issues
  ADD CONSTRAINT billing_reconciliation_issues_issue_type_check
  CHECK (issue_type IN ('unknown_order', 'amount_mismatch', 'provider_mismatch', 'processing_failure'));

CREATE INDEX IF NOT EXISTS idx_billing_checkout_orders_provider_status
  ON billing_checkout_orders(provider, status, created_at_ms DESC);
