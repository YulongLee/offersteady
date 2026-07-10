-- Shared Document Processing Pipeline baseline
-- Placeholder DDL for future Alembic migration translation.

CREATE TABLE IF NOT EXISTS processing_tasks (
  task_id TEXT PRIMARY KEY,
  document_id TEXT NOT NULL REFERENCES document_records(document_id),
  owner_user_id TEXT NOT NULL,
  document_kind TEXT NOT NULL,
  current_stage TEXT NOT NULL,
  retry_count INTEGER NOT NULL DEFAULT 0,
  max_retries INTEGER NOT NULL DEFAULT 0,
  parser_provider TEXT NOT NULL,
  embedding_provider TEXT NOT NULL,
  chunk_count INTEGER NOT NULL DEFAULT 0,
  error_code TEXT NULL,
  error_message TEXT NULL,
  created_at_ms BIGINT NOT NULL,
  updated_at_ms BIGINT NOT NULL,
  queued_at_ms BIGINT NULL,
  started_at_ms BIGINT NULL,
  completed_at_ms BIGINT NULL,
  last_retry_at_ms BIGINT NULL
);

CREATE INDEX IF NOT EXISTS idx_processing_tasks_owner_document
  ON processing_tasks (owner_user_id, document_id, updated_at_ms DESC);

CREATE INDEX IF NOT EXISTS idx_processing_tasks_stage_updated
  ON processing_tasks (current_stage, updated_at_ms DESC);

CREATE TABLE IF NOT EXISTS processing_task_events (
  event_id TEXT PRIMARY KEY,
  task_id TEXT NOT NULL REFERENCES processing_tasks(task_id),
  stage TEXT NOT NULL,
  retry_count INTEGER NOT NULL DEFAULT 0,
  event_name TEXT NOT NULL,
  duration_ms BIGINT NULL,
  error_code TEXT NULL,
  created_at_ms BIGINT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_processing_task_events_task_created
  ON processing_task_events (task_id, created_at_ms DESC);
