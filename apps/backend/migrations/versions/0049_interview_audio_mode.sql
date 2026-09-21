ALTER TABLE interview_sessions
  ADD COLUMN IF NOT EXISTS interview_audio_mode TEXT NOT NULL DEFAULT 'computer';

UPDATE interview_sessions
SET interview_audio_mode = 'computer'
WHERE interview_audio_mode IS NULL OR interview_audio_mode NOT IN ('computer', 'mobile');

ALTER TABLE interview_sessions
  DROP CONSTRAINT IF EXISTS ck_interview_sessions_audio_mode;

ALTER TABLE interview_sessions
  ADD CONSTRAINT ck_interview_sessions_audio_mode
  CHECK (interview_audio_mode IN ('computer', 'mobile')) NOT VALID;

ALTER TABLE interview_sessions
  VALIDATE CONSTRAINT ck_interview_sessions_audio_mode;
