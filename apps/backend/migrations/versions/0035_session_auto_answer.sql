ALTER TABLE interview_sessions
  ADD COLUMN IF NOT EXISTS auto_answer_enabled BOOLEAN NOT NULL DEFAULT FALSE;

ALTER TABLE interview_sessions
  ADD COLUMN IF NOT EXISTS auto_answer_enabled_at_ms BIGINT NULL;
