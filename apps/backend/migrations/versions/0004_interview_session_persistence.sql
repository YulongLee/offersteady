-- Persistent interview sessions, material bindings, context entries, and usage records.

CREATE TABLE IF NOT EXISTS interview_sessions (
  session_id TEXT PRIMARY KEY,
  owner_user_id TEXT NOT NULL,
  title TEXT NOT NULL,
  status TEXT NOT NULL,
  continue_target TEXT NOT NULL,
  material_binding_json JSONB NOT NULL,
  config_snapshot_json JSONB NOT NULL,
  usage_totals_json JSONB NOT NULL,
  integration_references_json JSONB NOT NULL,
  restart_of_session_id TEXT NULL,
  started_at_ms BIGINT NULL,
  ended_at_ms BIGINT NULL,
  created_at_ms BIGINT NOT NULL,
  updated_at_ms BIGINT NOT NULL,
  last_activity_at_ms BIGINT NOT NULL,
  deleted_at_ms BIGINT NULL
);

CREATE INDEX IF NOT EXISTS idx_interview_sessions_owner_updated
  ON interview_sessions (owner_user_id, updated_at_ms DESC);

CREATE TABLE IF NOT EXISTS interview_session_context_entries (
  entry_id TEXT PRIMARY KEY,
  session_id TEXT NOT NULL,
  owner_user_id TEXT NOT NULL,
  ordering INTEGER NOT NULL,
  created_at_ms BIGINT NOT NULL,
  entry_json JSONB NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_interview_session_context_entries_session_order
  ON interview_session_context_entries (session_id, ordering, created_at_ms);

CREATE TABLE IF NOT EXISTS interview_session_usage_records (
  usage_id TEXT PRIMARY KEY,
  session_id TEXT NOT NULL,
  owner_user_id TEXT NOT NULL,
  created_at_ms BIGINT NOT NULL,
  usage_json JSONB NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_interview_session_usage_records_session_created
  ON interview_session_usage_records (session_id, created_at_ms);
