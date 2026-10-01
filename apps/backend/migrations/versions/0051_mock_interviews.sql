-- Additive mock-interview storage. Existing session defaults and rows are unchanged.
ALTER TABLE interview_sessions DROP CONSTRAINT IF EXISTS ck_interview_sessions_session_mode;
ALTER TABLE interview_sessions ADD CONSTRAINT ck_interview_sessions_session_mode
  CHECK (session_mode IN ('interview', 'written', 'mock')) NOT VALID;
ALTER TABLE interview_sessions VALIDATE CONSTRAINT ck_interview_sessions_session_mode;

CREATE TABLE IF NOT EXISTS mock_interviews (
  session_id TEXT PRIMARY KEY REFERENCES interview_sessions(session_id),
  owner_user_id TEXT NOT NULL,
  idempotency_key TEXT NOT NULL,
  billing_class TEXT NOT NULL CHECK (billing_class IN ('daily_pass_free', 'points')),
  quota_day DATE NOT NULL,
  refunded BOOLEAN NOT NULL DEFAULT FALSE,
  created_at_ms BIGINT NOT NULL,
  updated_at_ms BIGINT NOT NULL,
  deleted_at_ms BIGINT,
  revision BIGINT NOT NULL DEFAULT 0,
  data JSONB NOT NULL,
  UNIQUE (owner_user_id, idempotency_key)
);
CREATE INDEX IF NOT EXISTS idx_mock_owner_history ON mock_interviews(owner_user_id, created_at_ms DESC)
  WHERE deleted_at_ms IS NULL;
CREATE INDEX IF NOT EXISTS idx_mock_daily_quota ON mock_interviews(owner_user_id, quota_day)
  WHERE billing_class = 'daily_pass_free' AND NOT refunded;

ALTER TABLE points_redemption_ledger DROP CONSTRAINT IF EXISTS points_redemption_ledger_kind_check;
ALTER TABLE points_redemption_ledger DROP CONSTRAINT IF EXISTS points_redemption_ledger_points_check;
ALTER TABLE points_redemption_ledger ADD CONSTRAINT points_redemption_ledger_kind_check CHECK (kind IN (
  'welcome_grant','redemption_credit','purchase_credit','referral_credit','referral_invitee_credit',
  'knowledge_index_settlement','redemption_reversal','answer_settlement','screenshot_answer_settlement',
  'realtime_minute_settlement','written_exam_entry_settlement','pass_usage','admin_adjustment',
  'mock_interview_entry_settlement','mock_interview_minute_settlement','mock_interview_refund'
));
ALTER TABLE points_redemption_ledger ADD CONSTRAINT points_redemption_ledger_points_check CHECK (
  (kind IN ('welcome_grant','redemption_credit','purchase_credit','referral_credit','referral_invitee_credit','mock_interview_refund') AND points > 0)
  OR (kind IN ('knowledge_index_settlement','redemption_reversal','answer_settlement','screenshot_answer_settlement',
              'realtime_minute_settlement','written_exam_entry_settlement','mock_interview_entry_settlement','mock_interview_minute_settlement') AND points < 0)
  OR (kind = 'pass_usage' AND points = 0)
  OR (kind = 'admin_adjustment' AND points <> 0)
);
