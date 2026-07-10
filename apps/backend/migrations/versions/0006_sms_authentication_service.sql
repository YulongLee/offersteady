-- SMS authentication service: users, identity bindings, sessions, and SMS challenge audit metadata.
-- Additive only; no plaintext SMS verification code is stored.

CREATE TABLE IF NOT EXISTS auth_users (
  user_id TEXT PRIMARY KEY,
  login_id TEXT NOT NULL UNIQUE,
  password_hash TEXT NOT NULL,
  display_name TEXT NOT NULL,
  avatar_url TEXT NULL,
  last_login_provider TEXT NOT NULL,
  last_login_at_ms BIGINT NOT NULL,
  created_at_ms BIGINT NOT NULL,
  updated_at_ms BIGINT NOT NULL,
  membership_anchor_ref TEXT NULL
);

CREATE TABLE IF NOT EXISTS auth_identity_bindings (
  binding_id TEXT PRIMARY KEY,
  user_id TEXT NOT NULL REFERENCES auth_users(user_id) ON DELETE CASCADE,
  provider TEXT NOT NULL,
  provider_subject TEXT NOT NULL,
  provider_subject_hint TEXT NOT NULL,
  avatar_url TEXT NULL,
  display_name TEXT NULL,
  status TEXT NOT NULL,
  bound_at_ms BIGINT NOT NULL,
  UNIQUE(provider, provider_subject)
);

CREATE INDEX IF NOT EXISTS idx_auth_identity_bindings_user ON auth_identity_bindings(user_id);

CREATE TABLE IF NOT EXISTS auth_sessions (
  auth_session_id TEXT PRIMARY KEY,
  user_id TEXT NOT NULL REFERENCES auth_users(user_id) ON DELETE CASCADE,
  client_label TEXT NOT NULL,
  refresh_token_fingerprint TEXT NOT NULL UNIQUE,
  status TEXT NOT NULL,
  issued_at_ms BIGINT NOT NULL,
  expires_at_ms BIGINT NOT NULL,
  last_used_at_ms BIGINT NOT NULL,
  revoked_at_ms BIGINT NULL
);

CREATE INDEX IF NOT EXISTS idx_auth_sessions_user_status ON auth_sessions(user_id, status);

CREATE TABLE IF NOT EXISTS auth_sms_challenges (
  challenge_id TEXT PRIMARY KEY,
  phone_e164 TEXT NOT NULL,
  phone_hash TEXT NOT NULL,
  provider TEXT NOT NULL,
  status TEXT NOT NULL,
  provider_biz_id TEXT NULL,
  provider_request_id TEXT NULL,
  attempt_count INTEGER NOT NULL DEFAULT 0,
  max_attempts INTEGER NOT NULL,
  expires_at_ms BIGINT NOT NULL,
  created_at_ms BIGINT NOT NULL,
  updated_at_ms BIGINT NOT NULL,
  last_error_code TEXT NULL,
  verified_at_ms BIGINT NULL
);

CREATE INDEX IF NOT EXISTS idx_auth_sms_challenges_phone_created ON auth_sms_challenges(phone_hash, created_at_ms DESC);
CREATE INDEX IF NOT EXISTS idx_auth_sms_challenges_status ON auth_sms_challenges(status, expires_at_ms);
