-- Unified Document Service metadata baseline
-- Placeholder DDL for future Alembic migration translation.

CREATE TABLE IF NOT EXISTS document_records (
  document_id TEXT PRIMARY KEY,
  owner_user_id TEXT NOT NULL,
  document_kind TEXT NOT NULL,
  display_name TEXT NOT NULL,
  file_kind TEXT NOT NULL,
  content_type TEXT NOT NULL,
  size_bytes BIGINT NOT NULL,
  object_key TEXT NOT NULL UNIQUE,
  status TEXT NOT NULL,
  knowledge_collection_id TEXT NULL,
  processing_requested_at_ms BIGINT NULL,
  deleted_at_ms BIGINT NULL,
  created_at_ms BIGINT NOT NULL,
  updated_at_ms BIGINT NOT NULL,
  summary TEXT NULL
);

CREATE INDEX IF NOT EXISTS idx_document_records_owner_kind_status
  ON document_records (owner_user_id, document_kind, status);

CREATE INDEX IF NOT EXISTS idx_document_records_collection
  ON document_records (knowledge_collection_id);
