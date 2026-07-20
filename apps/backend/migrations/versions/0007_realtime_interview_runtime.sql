BEGIN;

CREATE TABLE IF NOT EXISTS approved_realtime_transcripts (
  session_id TEXT NOT NULL,
  owner_user_id TEXT NOT NULL,
  segment_id TEXT NOT NULL,
  role TEXT NOT NULL CHECK (role IN ('candidate', 'interviewer')),
  transcript_text TEXT NOT NULL,
  created_at_ms BIGINT NOT NULL,
  expires_at_ms BIGINT NOT NULL,
  PRIMARY KEY (session_id, segment_id)
);

CREATE INDEX IF NOT EXISTS idx_approved_realtime_transcripts_owner_expiry
  ON approved_realtime_transcripts (owner_user_id, expires_at_ms);

COMMIT;

-- Rollback: DROP TABLE IF EXISTS approved_realtime_transcripts;
