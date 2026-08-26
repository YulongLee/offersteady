ALTER TABLE interview_sessions
  ADD COLUMN IF NOT EXISTS interview_language TEXT NOT NULL DEFAULT 'zh-CN';

UPDATE interview_sessions
SET interview_language = 'zh-CN'
WHERE interview_language IS NULL OR interview_language NOT IN ('zh-CN', 'en-US');

ALTER TABLE interview_sessions
  DROP CONSTRAINT IF EXISTS interview_sessions_interview_language_check;

ALTER TABLE interview_sessions
  ADD CONSTRAINT interview_sessions_interview_language_check
  CHECK (interview_language IN ('zh-CN', 'en-US')) NOT VALID;

ALTER TABLE interview_sessions
  VALIDATE CONSTRAINT interview_sessions_interview_language_check;
