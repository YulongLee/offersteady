-- Restore sessions that the historical per-session idle reconciler incorrectly
-- ended before the user ever started the interview. Deleted sessions and every
-- session with a real start timestamp remain untouched.
UPDATE interview_sessions
SET status = 'preparing',
    continue_target = 'preparing',
    ended_at_ms = NULL,
    updated_at_ms = GREATEST(updated_at_ms, (EXTRACT(EPOCH FROM NOW()) * 1000)::BIGINT),
    last_activity_at_ms = GREATEST(last_activity_at_ms, (EXTRACT(EPOCH FROM NOW()) * 1000)::BIGINT)
WHERE status = 'ended'
  AND started_at_ms IS NULL
  AND deleted_at_ms IS NULL;
