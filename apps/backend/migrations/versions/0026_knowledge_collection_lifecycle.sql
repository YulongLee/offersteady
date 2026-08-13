CREATE TABLE IF NOT EXISTS material_knowledge_collections (
  collection_id TEXT PRIMARY KEY,
  owner_user_id TEXT NOT NULL,
  name TEXT NOT NULL,
  created_at_ms BIGINT NOT NULL,
  updated_at_ms BIGINT NOT NULL,
  deleted_at_ms BIGINT NULL
);

ALTER TABLE material_knowledge_collections
  ADD COLUMN IF NOT EXISTS deleted_at_ms BIGINT NULL;

CREATE INDEX IF NOT EXISTS idx_material_knowledge_collections_owner_active
  ON material_knowledge_collections (owner_user_id, updated_at_ms DESC)
  WHERE deleted_at_ms IS NULL;
