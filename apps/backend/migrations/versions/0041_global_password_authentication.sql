-- Purpose-bind Global email challenges used for registration and password recovery.
-- Additive and safe for existing passwordless challenges and domestic deployments.

ALTER TABLE auth_email_challenges
  ADD COLUMN IF NOT EXISTS purpose TEXT NOT NULL DEFAULT 'login';

CREATE INDEX IF NOT EXISTS idx_auth_email_challenges_email_purpose_created
  ON auth_email_challenges(email_hash, purpose, created_at_ms DESC);
