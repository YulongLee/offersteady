ALTER TABLE interview_sessions
  ADD COLUMN IF NOT EXISTS session_mode TEXT NOT NULL DEFAULT 'interview';

UPDATE interview_sessions
SET session_mode = 'interview'
WHERE session_mode IS NULL OR session_mode NOT IN ('interview', 'written');

ALTER TABLE interview_sessions
  DROP CONSTRAINT IF EXISTS ck_interview_sessions_session_mode;

ALTER TABLE interview_sessions
  ADD CONSTRAINT ck_interview_sessions_session_mode
  CHECK (session_mode IN ('interview', 'written')) NOT VALID;

ALTER TABLE interview_sessions
  VALIDATE CONSTRAINT ck_interview_sessions_session_mode;
