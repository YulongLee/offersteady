-- Global email authentication challenges. Additive and safe for domestic deployments.
-- Full destinations and raw verification codes are intentionally not persisted here.

CREATE TABLE IF NOT EXISTS auth_email_challenges (
  challenge_id TEXT PRIMARY KEY,
  email_hash TEXT NOT NULL,
  masked_email TEXT NOT NULL,
  provider TEXT NOT NULL,
  status TEXT NOT NULL,
  provider_message_id TEXT NULL,
  provider_request_id TEXT NULL,
  attempt_count INTEGER NOT NULL DEFAULT 0,
  max_attempts INTEGER NOT NULL,
  expires_at_ms BIGINT NOT NULL,
  created_at_ms BIGINT NOT NULL,
  updated_at_ms BIGINT NOT NULL,
  last_error_code TEXT NULL,
  verified_at_ms BIGINT NULL,
  code_digest TEXT NULL
);

CREATE INDEX IF NOT EXISTS idx_auth_email_challenges_email_created
  ON auth_email_challenges(email_hash, created_at_ms DESC);
CREATE INDEX IF NOT EXISTS idx_auth_email_challenges_status
  ON auth_email_challenges(status, expires_at_ms);
