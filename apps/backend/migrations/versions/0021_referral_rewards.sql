-- Configurable, one-time referral rewards backed by the immutable points ledger.

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

CREATE TABLE IF NOT EXISTS growth_referral_settings (
  settings_id TEXT PRIMARY KEY CHECK (settings_id = 'default'),
  enabled BOOLEAN NOT NULL DEFAULT FALSE,
  reward_points INTEGER NOT NULL DEFAULT 500 CHECK (reward_points BETWEEN 1 AND 100000),
  config_version INTEGER NOT NULL DEFAULT 1 CHECK (config_version > 0),
  updated_by_user_id TEXT NULL,
  updated_at_ms BIGINT NOT NULL
);

INSERT INTO growth_referral_settings (
  settings_id, enabled, reward_points, config_version, updated_at_ms
) VALUES ('default', FALSE, 500, 1, 0)
ON CONFLICT (settings_id) DO NOTHING;

CREATE TABLE IF NOT EXISTS growth_referral_codes (
  user_id TEXT PRIMARY KEY,
  referral_code TEXT NOT NULL UNIQUE CHECK (CHAR_LENGTH(referral_code) BETWEEN 12 AND 48),
  status TEXT NOT NULL DEFAULT 'active' CHECK (status IN ('active', 'revoked')),
  created_at_ms BIGINT NOT NULL
);

CREATE TABLE IF NOT EXISTS growth_referral_activations (
  activation_id TEXT PRIMARY KEY,
  inviter_user_id TEXT NOT NULL,
  invitee_user_id TEXT NOT NULL UNIQUE,
  referral_code TEXT NOT NULL,
  reward_points INTEGER NOT NULL CHECK (reward_points > 0),
  config_version INTEGER NOT NULL CHECK (config_version > 0),
  ledger_reference_id TEXT NOT NULL UNIQUE,
  activated_at_ms BIGINT NOT NULL,
  CHECK (inviter_user_id <> invitee_user_id)
);

CREATE INDEX IF NOT EXISTS idx_growth_referral_activations_inviter
  ON growth_referral_activations(inviter_user_id, activated_at_ms DESC);
