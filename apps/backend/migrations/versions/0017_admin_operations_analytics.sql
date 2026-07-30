-- Long-lived, aggregate-only operations analytics. No user-level payloads are stored.

CREATE TABLE IF NOT EXISTS admin_metric_snapshots (
  bucket_start_ms BIGINT NOT NULL,
  granularity TEXT NOT NULL CHECK (granularity IN ('hourly', 'daily')),
  metric_key TEXT NOT NULL,
  metric_value DOUBLE PRECISION NULL,
  sample_count BIGINT NOT NULL DEFAULT 0 CHECK (sample_count >= 0),
  coverage_state TEXT NOT NULL CHECK (coverage_state IN ('complete', 'partial', 'unavailable')),
  definition_version INTEGER NOT NULL DEFAULT 1 CHECK (definition_version > 0),
  computed_at_ms BIGINT NOT NULL,
  PRIMARY KEY (bucket_start_ms, granularity, metric_key)
);

CREATE INDEX IF NOT EXISTS idx_admin_metric_snapshots_metric_range
  ON admin_metric_snapshots(metric_key, granularity, bucket_start_ms DESC);

CREATE TABLE IF NOT EXISTS admin_metric_aggregation_runs (
  run_id TEXT PRIMARY KEY,
  run_kind TEXT NOT NULL CHECK (run_kind IN ('scheduled', 'backfill', 'manual')),
  granularity TEXT NOT NULL CHECK (granularity IN ('hourly', 'daily')),
  range_started_at_ms BIGINT NOT NULL,
  range_ended_at_ms BIGINT NOT NULL,
  status TEXT NOT NULL CHECK (status IN ('running', 'completed', 'failed', 'skipped')),
  bucket_count INTEGER NOT NULL DEFAULT 0 CHECK (bucket_count >= 0),
  metric_count INTEGER NOT NULL DEFAULT 0 CHECK (metric_count >= 0),
  safe_error_code TEXT NULL,
  started_at_ms BIGINT NOT NULL,
  completed_at_ms BIGINT NULL
);

CREATE INDEX IF NOT EXISTS idx_admin_metric_runs_started
  ON admin_metric_aggregation_runs(started_at_ms DESC);

