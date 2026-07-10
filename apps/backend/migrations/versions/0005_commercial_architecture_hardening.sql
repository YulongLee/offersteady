-- Commercial architecture hardening: durable jobs, artifact manifest, AI usage and RAG traces.
-- Additive only: does not delete or rewrite existing user material data.

CREATE TABLE IF NOT EXISTS material_artifacts (
  artifact_id TEXT PRIMARY KEY,
  owner_user_id TEXT NOT NULL,
  document_id TEXT NOT NULL,
  document_version_id TEXT NOT NULL,
  document_kind TEXT NOT NULL,
  artifact_kind TEXT NOT NULL,
  object_key TEXT NOT NULL,
  sync_status TEXT NOT NULL,
  required BOOLEAN NOT NULL DEFAULT TRUE,
  content_type TEXT NULL,
  size_bytes BIGINT NULL,
  sha256 TEXT NULL,
  verified_at_ms BIGINT NULL,
  created_at_ms BIGINT NOT NULL,
  updated_at_ms BIGINT NOT NULL,
  safe_error_code TEXT NULL,
  UNIQUE(owner_user_id, document_version_id, artifact_kind)
);

CREATE INDEX IF NOT EXISTS idx_material_artifacts_owner_version ON material_artifacts(owner_user_id, document_version_id);
CREATE INDEX IF NOT EXISTS idx_material_artifacts_object_key ON material_artifacts(object_key);

CREATE TABLE IF NOT EXISTS material_processing_jobs (
  job_id TEXT PRIMARY KEY,
  owner_user_id TEXT NOT NULL,
  status TEXT NOT NULL,
  stage TEXT NOT NULL,
  document_id TEXT NULL,
  document_version_id TEXT NULL,
  related_task_id TEXT NULL,
  retry_count INTEGER NOT NULL DEFAULT 0,
  max_retries INTEGER NOT NULL DEFAULT 3,
  safe_error_code TEXT NULL,
  payload_json JSONB NOT NULL DEFAULT '{}'::jsonb,
  created_at_ms BIGINT NOT NULL,
  updated_at_ms BIGINT NOT NULL,
  scheduled_after_ms BIGINT NOT NULL DEFAULT 0,
  started_at_ms BIGINT NULL,
  completed_at_ms BIGINT NULL
);

CREATE TABLE IF NOT EXISTS material_deletion_jobs (LIKE material_processing_jobs INCLUDING ALL);
CREATE TABLE IF NOT EXISTS material_reconcile_jobs (LIKE material_processing_jobs INCLUDING ALL);

CREATE INDEX IF NOT EXISTS idx_material_processing_jobs_claim ON material_processing_jobs(status, scheduled_after_ms, created_at_ms);
CREATE INDEX IF NOT EXISTS idx_material_deletion_jobs_claim ON material_deletion_jobs(status, scheduled_after_ms, created_at_ms);
CREATE INDEX IF NOT EXISTS idx_material_reconcile_jobs_claim ON material_reconcile_jobs(status, scheduled_after_ms, created_at_ms);

CREATE TABLE IF NOT EXISTS ai_usage_records (
  usage_id TEXT PRIMARY KEY,
  owner_user_id TEXT NOT NULL,
  operation_kind TEXT NOT NULL,
  provider TEXT NOT NULL,
  model TEXT NOT NULL,
  status TEXT NOT NULL,
  related_job_id TEXT NULL,
  related_task_id TEXT NULL,
  session_id TEXT NULL,
  document_id TEXT NULL,
  document_version_id TEXT NULL,
  trace_id TEXT NULL,
  input_units INTEGER NULL,
  output_units INTEGER NULL,
  total_units INTEGER NULL,
  point_cost INTEGER NULL,
  duration_ms INTEGER NULL,
  safe_error_code TEXT NULL,
  created_at_ms BIGINT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_ai_usage_owner_created ON ai_usage_records(owner_user_id, created_at_ms DESC);
CREATE INDEX IF NOT EXISTS idx_ai_usage_trace ON ai_usage_records(trace_id);

CREATE TABLE IF NOT EXISTS rag_retrieval_traces (
  trace_id TEXT PRIMARY KEY,
  owner_user_id TEXT NOT NULL,
  session_id TEXT NULL,
  query_hash TEXT NOT NULL,
  strategy TEXT NOT NULL,
  filter_document_ids TEXT[] NOT NULL DEFAULT '{}',
  filter_document_version_ids TEXT[] NOT NULL DEFAULT '{}',
  candidate_count INTEGER NOT NULL,
  reranked_count INTEGER NOT NULL,
  returned_count INTEGER NOT NULL,
  returned_source_ids TEXT[] NOT NULL DEFAULT '{}',
  safe_error_code TEXT NULL,
  created_at_ms BIGINT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_rag_traces_owner_created ON rag_retrieval_traces(owner_user_id, created_at_ms DESC);
CREATE INDEX IF NOT EXISTS idx_rag_traces_session ON rag_retrieval_traces(session_id);
