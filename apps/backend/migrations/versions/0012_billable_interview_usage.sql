-- Durable, idempotent billing reservations for interview answers.

ALTER TABLE points_redemption_ledger
  DROP CONSTRAINT IF EXISTS points_redemption_ledger_kind_check;
ALTER TABLE points_redemption_ledger
  DROP CONSTRAINT IF EXISTS points_redemption_ledger_points_check;
ALTER TABLE points_redemption_ledger
  ADD CONSTRAINT points_redemption_ledger_kind_check CHECK (
    kind IN (
      'welcome_grant', 'redemption_credit', 'purchase_credit',
      'knowledge_index_settlement', 'redemption_reversal',
      'answer_settlement', 'screenshot_answer_settlement', 'pass_usage'
    )
  );
ALTER TABLE points_redemption_ledger
  ADD CONSTRAINT points_redemption_ledger_points_check CHECK (
    (kind IN ('welcome_grant', 'redemption_credit', 'purchase_credit') AND points > 0)
    OR (kind IN (
      'knowledge_index_settlement', 'redemption_reversal',
      'answer_settlement', 'screenshot_answer_settlement'
    ) AND points < 0)
    OR (kind = 'pass_usage' AND points = 0)
  );

CREATE TABLE IF NOT EXISTS billing_usage_reservations (
  reservation_id TEXT PRIMARY KEY,
  usage_id TEXT NOT NULL UNIQUE,
  user_id TEXT NOT NULL,
  usage_kind TEXT NOT NULL CHECK (usage_kind IN ('answer', 'screenshot_answer')),
  points_reserved INTEGER NOT NULL CHECK (points_reserved >= 0),
  billing_source TEXT NOT NULL CHECK (billing_source IN ('points', 'time_pass')),
  status TEXT NOT NULL CHECK (status IN ('reserved', 'settled', 'released')),
  created_at_ms BIGINT NOT NULL,
  settled_at_ms BIGINT NULL,
  released_at_ms BIGINT NULL
);

CREATE INDEX IF NOT EXISTS idx_billing_usage_reservations_user_status
  ON billing_usage_reservations(user_id, status);
