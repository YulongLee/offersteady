CREATE TABLE IF NOT EXISTS baidu_ranking_keywords (
  keyword_id TEXT PRIMARY KEY,
  domain TEXT NOT NULL,
  keyword TEXT NOT NULL,
  status TEXT NOT NULL DEFAULT 'active' CHECK (status IN ('active', 'inactive')),
  created_at_ms BIGINT NOT NULL,
  updated_at_ms BIGINT NOT NULL,
  UNIQUE (domain, keyword)
);

CREATE TABLE IF NOT EXISTS baidu_ranking_snapshots (
  snapshot_id TEXT PRIMARY KEY,
  keyword_id TEXT NOT NULL REFERENCES baidu_ranking_keywords(keyword_id) ON DELETE CASCADE,
  domain TEXT NOT NULL,
  keyword TEXT NOT NULL,
  observed_date DATE NOT NULL,
  observed_at_ms BIGINT NOT NULL,
  status TEXT NOT NULL CHECK (status IN ('ranked', 'not_found', 'provider_error', 'timeout', 'invalid_config')),
  results_json JSONB NOT NULL DEFAULT '[]'::jsonb,
  top_rank INTEGER NULL,
  matched_url TEXT NULL,
  matched_title TEXT NULL,
  duration_ms INTEGER NULL,
  safe_error_code TEXT NULL,
  created_at_ms BIGINT NOT NULL,
  UNIQUE (keyword_id, observed_date)
);

CREATE INDEX IF NOT EXISTS idx_baidu_ranking_snapshots_keyword_date
  ON baidu_ranking_snapshots(keyword_id, observed_date DESC);
