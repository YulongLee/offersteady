-- Durable upload-intent and document-processing runtime state.
-- Additive only: existing material documents and OSS objects are not rewritten.

CREATE TABLE IF NOT EXISTS material_upload_intent_reservations (
  intent_id TEXT PRIMARY KEY,
  owner_user_id TEXT NOT NULL,
  material_kind TEXT NOT NULL,
  filename TEXT NOT NULL,
  file_kind TEXT NOT NULL,
  content_type TEXT NOT NULL,
  object_key TEXT NOT NULL,
  upload_url TEXT NOT NULL,
  upload_fields_json JSONB NOT NULL DEFAULT '{}'::jsonb,
  issued_at_ms BIGINT NOT NULL,
  expires_at_ms BIGINT NOT NULL,
  object_id TEXT NULL,
  document_id TEXT NULL,
  document_version_id TEXT NULL,
  upload_method TEXT NOT NULL DEFAULT 'POST'
);

CREATE INDEX IF NOT EXISTS idx_material_upload_intent_reservations_expiry
  ON material_upload_intent_reservations(expires_at_ms);

CREATE TABLE IF NOT EXISTS material_processing_tasks (
  task_id TEXT PRIMARY KEY,
  document_id TEXT NOT NULL,
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
  last_retry_at_ms BIGINT NULL,
  billing_quote_id TEXT NULL
);

ALTER TABLE material_processing_tasks
  ADD COLUMN IF NOT EXISTS billing_quote_id TEXT NULL;

CREATE INDEX IF NOT EXISTS idx_material_processing_tasks_owner_document
  ON material_processing_tasks(owner_user_id, document_id, updated_at_ms DESC);

CREATE INDEX IF NOT EXISTS idx_material_processing_tasks_stage_updated
  ON material_processing_tasks(current_stage, updated_at_ms DESC);

CREATE TABLE IF NOT EXISTS material_processing_task_events (
  event_id TEXT PRIMARY KEY,
  task_id TEXT NOT NULL REFERENCES material_processing_tasks(task_id) ON DELETE CASCADE,
  stage TEXT NOT NULL,
  retry_count INTEGER NOT NULL DEFAULT 0,
  event_name TEXT NOT NULL,
  duration_ms BIGINT NULL,
  error_code TEXT NULL,
  created_at_ms BIGINT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_material_processing_task_events_task_created
  ON material_processing_task_events(task_id, created_at_ms DESC);

DO $$
BEGIN
  IF EXISTS (
    SELECT 1
    FROM information_schema.columns
    WHERE table_schema = current_schema()
      AND table_name = 'material_processing_jobs'
      AND column_name = 'related_task_id'
  ) THEN
    EXECUTE 'CREATE INDEX IF NOT EXISTS idx_material_processing_jobs_related_task '
      || 'ON material_processing_jobs(related_task_id)';
  END IF;
END $$;
