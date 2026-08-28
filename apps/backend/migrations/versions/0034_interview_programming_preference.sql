ALTER TABLE interview_sessions
  ADD COLUMN IF NOT EXISTS programming_required BOOLEAN NOT NULL DEFAULT FALSE;

ALTER TABLE interview_sessions
  ADD COLUMN IF NOT EXISTS programming_language TEXT NULL;

UPDATE interview_sessions
SET programming_language = NULL
WHERE programming_required = FALSE;

ALTER TABLE interview_sessions
  DROP CONSTRAINT IF EXISTS interview_sessions_programming_preference_check;

ALTER TABLE interview_sessions
  ADD CONSTRAINT interview_sessions_programming_preference_check CHECK (
    (programming_required = FALSE AND programming_language IS NULL)
    OR
    (programming_required = TRUE AND programming_language IN ('python', 'java', 'cpp', 'javascript', 'typescript', 'go'))
  );
