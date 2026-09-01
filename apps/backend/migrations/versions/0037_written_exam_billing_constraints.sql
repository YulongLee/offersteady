-- Accept the written-exam entry reservation and its wallet settlement.

ALTER TABLE billing_usage_reservations
  DROP CONSTRAINT IF EXISTS billing_usage_reservations_usage_kind_check;
ALTER TABLE billing_usage_reservations
  ADD CONSTRAINT billing_usage_reservations_usage_kind_check
  CHECK (usage_kind IN ('answer', 'screenshot_answer', 'realtime_minute', 'written_exam_entry'));

ALTER TABLE points_redemption_ledger
  DROP CONSTRAINT IF EXISTS points_redemption_ledger_kind_check;
ALTER TABLE points_redemption_ledger
  DROP CONSTRAINT IF EXISTS points_redemption_ledger_points_check;
ALTER TABLE points_redemption_ledger
  ADD CONSTRAINT points_redemption_ledger_kind_check CHECK (
    kind IN (
      'welcome_grant', 'redemption_credit', 'purchase_credit', 'referral_credit',
      'referral_invitee_credit', 'knowledge_index_settlement', 'redemption_reversal',
      'answer_settlement', 'screenshot_answer_settlement', 'realtime_minute_settlement',
      'written_exam_entry_settlement', 'pass_usage', 'admin_adjustment'
    )
  );
ALTER TABLE points_redemption_ledger
  ADD CONSTRAINT points_redemption_ledger_points_check CHECK (
    (kind IN (
      'welcome_grant', 'redemption_credit', 'purchase_credit',
      'referral_credit', 'referral_invitee_credit'
    ) AND points > 0)
    OR (kind IN (
      'knowledge_index_settlement', 'redemption_reversal', 'answer_settlement',
      'screenshot_answer_settlement', 'realtime_minute_settlement',
      'written_exam_entry_settlement'
    ) AND points < 0)
    OR (kind = 'pass_usage' AND points = 0)
    OR (kind = 'admin_adjustment' AND points <> 0)
  );
