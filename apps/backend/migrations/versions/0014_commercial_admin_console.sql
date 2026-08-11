-- Commercial admin console. Additive and disabled by application configuration.

CREATE TABLE IF NOT EXISTS admin_authorizations (
  authorization_id TEXT PRIMARY KEY,
  user_id TEXT NOT NULL UNIQUE REFERENCES auth_users(user_id) ON DELETE CASCADE,
  role TEXT NOT NULL CHECK (role IN ('super_admin', 'operations', 'support', 'finance', 'technical_auditor')),
  status TEXT NOT NULL CHECK (status IN ('active', 'disabled')),
  authorization_version INTEGER NOT NULL DEFAULT 1 CHECK (authorization_version > 0),
  totp_secret_ciphertext TEXT NOT NULL,
  created_by_user_id TEXT NULL,
  created_at_ms BIGINT NOT NULL,
  updated_at_ms BIGINT NOT NULL,
  disabled_at_ms BIGINT NULL
);

CREATE INDEX IF NOT EXISTS idx_admin_authorizations_status_role
  ON admin_authorizations(status, role);

CREATE TABLE IF NOT EXISTS admin_sessions (
  admin_session_id TEXT PRIMARY KEY,
  authorization_id TEXT NOT NULL REFERENCES admin_authorizations(authorization_id) ON DELETE CASCADE,
  user_id TEXT NOT NULL REFERENCES auth_users(user_id) ON DELETE CASCADE,
  token_fingerprint TEXT NOT NULL UNIQUE,
  authorization_version INTEGER NOT NULL,
  role TEXT NOT NULL,
  permissions_json JSONB NOT NULL,
  status TEXT NOT NULL CHECK (status IN ('active', 'revoked', 'expired')),
  issued_at_ms BIGINT NOT NULL,
  expires_at_ms BIGINT NOT NULL,
  recent_mfa_at_ms BIGINT NOT NULL,
  last_used_at_ms BIGINT NOT NULL,
  revoked_at_ms BIGINT NULL,
  ip_hash TEXT NULL,
  user_agent_hash TEXT NULL
);

CREATE INDEX IF NOT EXISTS idx_admin_sessions_user_status
  ON admin_sessions(user_id, status, expires_at_ms);

CREATE TABLE IF NOT EXISTS admin_audit_events (
  audit_event_id TEXT PRIMARY KEY,
  actor_user_id TEXT NULL,
  actor_role TEXT NULL,
  action TEXT NOT NULL,
  resource_type TEXT NOT NULL,
  resource_id TEXT NULL,
  reason TEXT NULL,
  request_id TEXT NOT NULL,
  result TEXT NOT NULL CHECK (result IN ('success', 'denied', 'failed')),
  safe_details_json JSONB NOT NULL DEFAULT '{}'::jsonb,
  source_ip_hash TEXT NULL,
  user_agent_hash TEXT NULL,
  created_at_ms BIGINT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_admin_audit_created
  ON admin_audit_events(created_at_ms DESC);
CREATE INDEX IF NOT EXISTS idx_admin_audit_actor_action
  ON admin_audit_events(actor_user_id, action, created_at_ms DESC);
CREATE INDEX IF NOT EXISTS idx_admin_audit_resource
  ON admin_audit_events(resource_type, resource_id, created_at_ms DESC);
CREATE INDEX IF NOT EXISTS idx_admin_audit_request
  ON admin_audit_events(request_id);

CREATE OR REPLACE FUNCTION prevent_admin_audit_mutation()
RETURNS trigger AS $$
BEGIN
  RAISE EXCEPTION 'admin audit events are immutable';
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trg_admin_audit_immutable ON admin_audit_events;
CREATE TRIGGER trg_admin_audit_immutable
BEFORE UPDATE OR DELETE ON admin_audit_events
FOR EACH ROW EXECUTE FUNCTION prevent_admin_audit_mutation();

CREATE TABLE IF NOT EXISTS admin_user_restrictions (
  restriction_id TEXT PRIMARY KEY,
  user_id TEXT NOT NULL UNIQUE REFERENCES auth_users(user_id) ON DELETE CASCADE,
  status TEXT NOT NULL CHECK (status IN ('active', 'revoked')),
  reason TEXT NOT NULL,
  created_by_user_id TEXT NOT NULL,
  created_at_ms BIGINT NOT NULL,
  updated_at_ms BIGINT NOT NULL,
  revoked_at_ms BIGINT NULL
);

CREATE INDEX IF NOT EXISTS idx_admin_user_restrictions_status
  ON admin_user_restrictions(status, updated_at_ms DESC);

CREATE TABLE IF NOT EXISTS admin_idempotency_records (
  actor_user_id TEXT NOT NULL,
  action TEXT NOT NULL,
  idempotency_key TEXT NOT NULL,
  result_json JSONB NOT NULL,
  created_at_ms BIGINT NOT NULL,
  PRIMARY KEY(actor_user_id, action, idempotency_key)
);

CREATE TABLE IF NOT EXISTS admin_time_entitlements (
  entitlement_id TEXT PRIMARY KEY,
  user_id TEXT NOT NULL REFERENCES auth_users(user_id) ON DELETE CASCADE,
  product_id TEXT NOT NULL DEFAULT 'admin-time-adjustment',
  starts_at_ms BIGINT NOT NULL,
  ends_at_ms BIGINT NOT NULL,
  reference_id TEXT NOT NULL UNIQUE,
  reason TEXT NOT NULL,
  created_by_user_id TEXT NOT NULL,
  created_at_ms BIGINT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_admin_time_entitlements_user_time
  ON admin_time_entitlements(user_id, starts_at_ms, ends_at_ms);

ALTER TABLE points_redemption_ledger
  DROP CONSTRAINT IF EXISTS points_redemption_ledger_kind_check;
ALTER TABLE points_redemption_ledger
  DROP CONSTRAINT IF EXISTS points_redemption_ledger_points_check;
ALTER TABLE points_redemption_ledger
  ADD CONSTRAINT points_redemption_ledger_kind_check CHECK (
    kind IN (
      'welcome_grant', 'redemption_credit', 'purchase_credit', 'referral_credit',
      'knowledge_index_settlement', 'redemption_reversal',
      'answer_settlement', 'screenshot_answer_settlement', 'pass_usage',
      'admin_adjustment'
    )
  );
ALTER TABLE points_redemption_ledger
  ADD CONSTRAINT points_redemption_ledger_points_check CHECK (
    (kind IN ('welcome_grant', 'redemption_credit', 'purchase_credit', 'referral_credit') AND points > 0)
    OR (kind IN (
      'knowledge_index_settlement', 'redemption_reversal',
      'answer_settlement', 'screenshot_answer_settlement'
    ) AND points < 0)
    OR (kind = 'pass_usage' AND points = 0)
    OR (kind = 'admin_adjustment' AND points <> 0)
  );
