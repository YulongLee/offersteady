-- Reconcile historical live rows before enforcing one active interview per user.
UPDATE interview_sessions
SET status = 'ended',
    continue_target = 'history',
    ended_at_ms = COALESCE(ended_at_ms, updated_at_ms)
WHERE status = 'live'
  AND (
    deleted_at_ms IS NOT NULL
    OR last_activity_at_ms < ((EXTRACT(EPOCH FROM NOW()) * 1000)::BIGINT - 1200000)
  );

WITH ranked AS (
  SELECT session_id,
         ROW_NUMBER() OVER (
           PARTITION BY owner_user_id
           ORDER BY last_activity_at_ms DESC, updated_at_ms DESC, session_id DESC
         ) AS position
  FROM interview_sessions
  WHERE status = 'live' AND deleted_at_ms IS NULL
)
UPDATE interview_sessions AS sessions
SET status = 'ended',
    continue_target = 'history',
    ended_at_ms = COALESCE(sessions.ended_at_ms, sessions.updated_at_ms)
FROM ranked
WHERE sessions.session_id = ranked.session_id AND ranked.position > 1;

CREATE UNIQUE INDEX IF NOT EXISTS uq_interview_sessions_one_live_per_user
  ON interview_sessions (owner_user_id)
  WHERE status = 'live' AND deleted_at_ms IS NULL;

CREATE INDEX IF NOT EXISTS idx_interview_sessions_live_activity
  ON interview_sessions (last_activity_at_ms)
  WHERE status = 'live' AND deleted_at_ms IS NULL;
