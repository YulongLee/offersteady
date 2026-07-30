-- Commercial admin redemption-code batches.
-- Plaintext codes are returned once and are never persisted.

CREATE TABLE IF NOT EXISTS admin_redemption_batches (
  batch_id TEXT PRIMARY KEY,
  actor_user_id TEXT NOT NULL REFERENCES auth_users(user_id),
  idempotency_key TEXT NOT NULL,
  campaign TEXT NOT NULL,
  reason TEXT NOT NULL,
  points_per_code INTEGER NOT NULL CHECK (points_per_code > 0),
  code_count INTEGER NOT NULL CHECK (code_count > 0),
  expires_at_ms BIGINT NOT NULL,
  created_at_ms BIGINT NOT NULL,
  UNIQUE(actor_user_id, idempotency_key)
);

ALTER TABLE points_redemption_codes
  ADD COLUMN IF NOT EXISTS batch_id TEXT NULL REFERENCES admin_redemption_batches(batch_id);
ALTER TABLE points_redemption_codes
  ADD COLUMN IF NOT EXISTS expires_at_ms BIGINT NULL;

CREATE INDEX IF NOT EXISTS idx_admin_redemption_batches_created
  ON admin_redemption_batches(created_at_ms DESC);
CREATE INDEX IF NOT EXISTS idx_points_redemption_codes_batch
  ON points_redemption_codes(batch_id, status);
CREATE INDEX IF NOT EXISTS idx_points_redemption_codes_expiry
  ON points_redemption_codes(status, expires_at_ms);
