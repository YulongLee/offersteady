-- Limit referral activation to the first 72 hours after registration and reward both users.

ALTER TABLE points_redemption_ledger
  DROP CONSTRAINT IF EXISTS points_redemption_ledger_kind_check;
ALTER TABLE points_redemption_ledger
  DROP CONSTRAINT IF EXISTS points_redemption_ledger_points_check;
ALTER TABLE points_redemption_ledger
  ADD CONSTRAINT points_redemption_ledger_kind_check CHECK (
    kind IN (
      'welcome_grant', 'redemption_credit', 'purchase_credit', 'referral_credit',
      'referral_invitee_credit', 'knowledge_index_settlement', 'redemption_reversal',
      'answer_settlement', 'screenshot_answer_settlement', 'pass_usage',
      'admin_adjustment'
    )
  );
ALTER TABLE points_redemption_ledger
  ADD CONSTRAINT points_redemption_ledger_points_check CHECK (
    (kind IN (
      'welcome_grant', 'redemption_credit', 'purchase_credit', 'referral_credit',
      'referral_invitee_credit'
    ) AND points > 0)
    OR (kind IN (
      'knowledge_index_settlement', 'redemption_reversal',
      'answer_settlement', 'screenshot_answer_settlement'
    ) AND points < 0)
    OR (kind = 'pass_usage' AND points = 0)
    OR (kind = 'admin_adjustment' AND points <> 0)
  );

ALTER TABLE growth_referral_settings
  ADD COLUMN IF NOT EXISTS invitee_reward_points INTEGER NOT NULL DEFAULT 500;
ALTER TABLE growth_referral_settings
  DROP CONSTRAINT IF EXISTS growth_referral_settings_invitee_reward_points_check;
ALTER TABLE growth_referral_settings
  ADD CONSTRAINT growth_referral_settings_invitee_reward_points_check
  CHECK (invitee_reward_points BETWEEN 1 AND 100000);

ALTER TABLE growth_referral_activations
  ADD COLUMN IF NOT EXISTS invitee_reward_points INTEGER NOT NULL DEFAULT 0;
ALTER TABLE growth_referral_activations
  ADD COLUMN IF NOT EXISTS invitee_ledger_reference_id TEXT NULL;
ALTER TABLE growth_referral_activations
  ADD COLUMN IF NOT EXISTS activation_deadline_ms BIGINT NULL;

CREATE UNIQUE INDEX IF NOT EXISTS idx_growth_referral_activations_invitee_ledger_reference
  ON growth_referral_activations(invitee_ledger_reference_id)
  WHERE invitee_ledger_reference_id IS NOT NULL;
