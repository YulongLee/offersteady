-- Complete knowledge-index billing for points and included member allowances.

ALTER TABLE billing_index_reservations
  DROP CONSTRAINT IF EXISTS billing_index_reservations_points_reserved_check,
  DROP CONSTRAINT IF EXISTS billing_index_reservations_points_reserved_check1;

ALTER TABLE billing_index_reservations
  ADD COLUMN IF NOT EXISTS billing_source TEXT NOT NULL DEFAULT 'points',
  ADD COLUMN IF NOT EXISTS entitlement_id TEXT NULL,
  ADD COLUMN IF NOT EXISTS allowance_reserved INTEGER NOT NULL DEFAULT 0;

ALTER TABLE billing_index_reservations
  ADD CONSTRAINT billing_index_reservations_points_reserved_check CHECK (points_reserved >= 0);

ALTER TABLE billing_index_reservations
  DROP CONSTRAINT IF EXISTS billing_index_reservations_billing_source_check;

ALTER TABLE billing_index_reservations
  ADD CONSTRAINT billing_index_reservations_billing_source_check
  CHECK (billing_source IN ('points', 'pass_allowance'));

CREATE INDEX IF NOT EXISTS idx_billing_index_reservations_entitlement_status
  ON billing_index_reservations(entitlement_id, status)
  WHERE entitlement_id IS NOT NULL;
