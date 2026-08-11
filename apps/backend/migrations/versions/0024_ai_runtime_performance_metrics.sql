ALTER TABLE ai_usage_records
  ADD COLUMN IF NOT EXISTS first_token_ms INTEGER NULL,
  ADD COLUMN IF NOT EXISTS final_latency_ms INTEGER NULL;

CREATE INDEX IF NOT EXISTS idx_ai_usage_operation_created
  ON ai_usage_records(operation_kind, created_at_ms DESC);
