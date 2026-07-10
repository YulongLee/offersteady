-- Commercial material persistence and RAG indexing baseline.
-- Placeholder DDL for future Alembic migration translation.

CREATE TABLE IF NOT EXISTS material_documents (
  document_id TEXT PRIMARY KEY,
  owner_user_id TEXT NOT NULL,
  document_kind TEXT NOT NULL,
  display_name TEXT NOT NULL,
  current_version_id TEXT NULL,
  status TEXT NOT NULL,
  knowledge_collection_id TEXT NULL,
  created_at_ms BIGINT NOT NULL,
  updated_at_ms BIGINT NOT NULL,
  deleted_at_ms BIGINT NULL
);

CREATE INDEX IF NOT EXISTS idx_material_documents_owner_kind_status
  ON material_documents (owner_user_id, document_kind, status);

CREATE INDEX IF NOT EXISTS idx_material_documents_collection
  ON material_documents (knowledge_collection_id);

CREATE TABLE IF NOT EXISTS material_document_versions (
  document_version_id TEXT PRIMARY KEY,
  document_id TEXT NOT NULL REFERENCES material_documents(document_id),
  owner_user_id TEXT NOT NULL,
  document_kind TEXT NOT NULL,
  display_name TEXT NOT NULL,
  original_filename TEXT NOT NULL,
  file_kind TEXT NOT NULL,
  content_type TEXT NOT NULL,
  size_bytes BIGINT NOT NULL,
  object_key TEXT NOT NULL UNIQUE,
  object_id TEXT NOT NULL,
  content_fingerprint TEXT NOT NULL,
  version INTEGER NOT NULL,
  lifecycle_status TEXT NOT NULL,
  index_state TEXT NOT NULL,
  page_count INTEGER NULL,
  token_count INTEGER NULL,
  chunk_count INTEGER NULL,
  safe_summary TEXT NULL,
  knowledge_collection_id TEXT NULL,
  created_at_ms BIGINT NOT NULL,
  updated_at_ms BIGINT NOT NULL,
  deleted_at_ms BIGINT NULL,
  UNIQUE (document_id, version),
  UNIQUE (owner_user_id, content_fingerprint, document_kind)
);

CREATE INDEX IF NOT EXISTS idx_material_versions_owner_kind_index
  ON material_document_versions (owner_user_id, document_kind, index_state, lifecycle_status);

CREATE INDEX IF NOT EXISTS idx_material_versions_document_updated
  ON material_document_versions (document_id, updated_at_ms DESC);

CREATE TABLE IF NOT EXISTS material_upload_intents (
  upload_intent_id TEXT PRIMARY KEY,
  owner_user_id TEXT NOT NULL,
  document_id TEXT NULL,
  document_version_id TEXT NULL,
  document_kind TEXT NOT NULL,
  filename TEXT NOT NULL,
  file_kind TEXT NOT NULL,
  content_type TEXT NOT NULL,
  size_bytes BIGINT NOT NULL,
  object_key TEXT NOT NULL UNIQUE,
  object_id TEXT NOT NULL,
  status TEXT NOT NULL,
  issued_at_ms BIGINT NOT NULL,
  expires_at_ms BIGINT NOT NULL,
  completed_at_ms BIGINT NULL
);

CREATE INDEX IF NOT EXISTS idx_material_upload_intents_owner_status
  ON material_upload_intents (owner_user_id, status, expires_at_ms);

CREATE TABLE IF NOT EXISTS material_processing_jobs (
  processing_job_id TEXT PRIMARY KEY,
  owner_user_id TEXT NOT NULL,
  document_id TEXT NOT NULL REFERENCES material_documents(document_id),
  document_version_id TEXT NOT NULL REFERENCES material_document_versions(document_version_id),
  idempotency_key TEXT NOT NULL,
  content_fingerprint TEXT NOT NULL,
  stage TEXT NOT NULL,
  status TEXT NOT NULL,
  retry_count INTEGER NOT NULL DEFAULT 0,
  parser_version TEXT NULL,
  embedding_model TEXT NULL,
  tokenizer_version TEXT NULL,
  safe_error_code TEXT NULL,
  created_at_ms BIGINT NOT NULL,
  updated_at_ms BIGINT NOT NULL,
  started_at_ms BIGINT NULL,
  completed_at_ms BIGINT NULL,
  UNIQUE (owner_user_id, idempotency_key)
);

CREATE INDEX IF NOT EXISTS idx_material_processing_jobs_status_updated
  ON material_processing_jobs (status, stage, updated_at_ms);

CREATE TABLE IF NOT EXISTS material_index_jobs (
  index_job_id TEXT PRIMARY KEY,
  owner_user_id TEXT NOT NULL,
  document_id TEXT NOT NULL REFERENCES material_documents(document_id),
  document_version_id TEXT NOT NULL REFERENCES material_document_versions(document_version_id),
  processing_job_id TEXT NULL REFERENCES material_processing_jobs(processing_job_id),
  quote_id TEXT NULL,
  usage_id TEXT NULL,
  status TEXT NOT NULL,
  funding_source TEXT NULL,
  point_cost INTEGER NULL,
  token_count INTEGER NULL,
  chunk_count INTEGER NULL,
  embedding_model TEXT NULL,
  embedding_dimension INTEGER NULL,
  catalog_version INTEGER NULL,
  safe_error_code TEXT NULL,
  created_at_ms BIGINT NOT NULL,
  updated_at_ms BIGINT NOT NULL,
  UNIQUE (owner_user_id, document_version_id, status)
);

CREATE INDEX IF NOT EXISTS idx_material_index_jobs_owner_status
  ON material_index_jobs (owner_user_id, status, updated_at_ms);

CREATE TABLE IF NOT EXISTS material_document_chunks (
  chunk_id TEXT PRIMARY KEY,
  owner_user_id TEXT NOT NULL,
  document_id TEXT NOT NULL REFERENCES material_documents(document_id),
  document_version_id TEXT NOT NULL REFERENCES material_document_versions(document_version_id),
  document_kind TEXT NOT NULL,
  collection_id TEXT NULL,
  ordinal INTEGER NOT NULL,
  content_hash TEXT NOT NULL,
  safe_summary TEXT NULL,
  text_excerpt TEXT NOT NULL,
  token_count INTEGER NOT NULL DEFAULT 0,
  embedding_model TEXT NOT NULL,
  embedding_dimension INTEGER NOT NULL,
  embedding vector(1536) NULL,
  created_at_ms BIGINT NOT NULL,
  UNIQUE (document_version_id, ordinal),
  UNIQUE (document_version_id, content_hash)
);

CREATE INDEX IF NOT EXISTS idx_material_chunks_owner_version
  ON material_document_chunks (owner_user_id, document_version_id, ordinal);

CREATE INDEX IF NOT EXISTS idx_material_chunks_owner_kind
  ON material_document_chunks (owner_user_id, document_kind);

CREATE INDEX IF NOT EXISTS idx_material_chunks_embedding_cosine
  ON material_document_chunks USING ivfflat (embedding vector_cosine_ops)
  WITH (lists = 100);

CREATE TABLE IF NOT EXISTS session_material_snapshots (
  snapshot_id TEXT PRIMARY KEY,
  session_id TEXT NOT NULL,
  owner_user_id TEXT NOT NULL,
  selection_revision INTEGER NOT NULL,
  source_id TEXT NOT NULL,
  document_id TEXT NOT NULL,
  document_version_id TEXT NOT NULL,
  display_name TEXT NOT NULL,
  source_kind TEXT NOT NULL,
  document_kind TEXT NOT NULL,
  source_version TEXT NOT NULL,
  index_state TEXT NOT NULL,
  deleted BOOLEAN NOT NULL DEFAULT FALSE,
  disabled BOOLEAN NOT NULL DEFAULT FALSE,
  safe_summary TEXT NULL,
  confirmed_at_ms BIGINT NOT NULL,
  UNIQUE (session_id, selection_revision, source_id)
);

CREATE INDEX IF NOT EXISTS idx_session_material_snapshots_session_revision
  ON session_material_snapshots (session_id, selection_revision);

CREATE INDEX IF NOT EXISTS idx_session_material_snapshots_owner_version
  ON session_material_snapshots (owner_user_id, document_version_id);

CREATE TABLE IF NOT EXISTS material_deletion_jobs (
  deletion_job_id TEXT PRIMARY KEY,
  owner_user_id TEXT NOT NULL,
  document_id TEXT NOT NULL,
  document_version_id TEXT NULL,
  status TEXT NOT NULL,
  raw_object_key TEXT NULL,
  processed_prefix TEXT NULL,
  vector_cleanup_required BOOLEAN NOT NULL DEFAULT TRUE,
  safe_error_code TEXT NULL,
  created_at_ms BIGINT NOT NULL,
  scheduled_at_ms BIGINT NOT NULL,
  completed_at_ms BIGINT NULL
);

CREATE INDEX IF NOT EXISTS idx_material_deletion_jobs_status_scheduled
  ON material_deletion_jobs (status, scheduled_at_ms);
