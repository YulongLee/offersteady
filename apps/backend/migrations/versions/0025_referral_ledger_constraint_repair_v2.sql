-- Re-assert referral ledger compatibility after every legacy initializer has
-- already run. This is a new migration id because an earlier repair may have
-- been recorded before another repository restored an older constraint.

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
