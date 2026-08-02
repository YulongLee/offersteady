-- Server-owned commercial catalog. Product benefits are fixed; administrators edit presentation and price only.

CREATE TABLE IF NOT EXISTS billing_catalog_products (
  product_id TEXT PRIMARY KEY,
  catalog_version INTEGER NOT NULL CHECK (catalog_version > 0),
  kind TEXT NOT NULL CHECK (kind IN ('time_pass', 'points_pack')),
  display_name TEXT NOT NULL CHECK (CHAR_LENGTH(display_name) BETWEEN 2 AND 40),
  price_cents INTEGER NOT NULL CHECK (price_cents > 0),
  points INTEGER NULL CHECK (points IS NULL OR points > 0),
  duration_days INTEGER NULL CHECK (duration_days IS NULL OR duration_days > 0),
  knowledge_index_allowance INTEGER NOT NULL DEFAULT 0 CHECK (knowledge_index_allowance >= 0),
  published BOOLEAN NOT NULL DEFAULT TRUE,
  updated_by_user_id TEXT NULL,
  created_at_ms BIGINT NOT NULL,
  updated_at_ms BIGINT NOT NULL,
  CHECK (
    (kind = 'time_pass' AND duration_days IN (1, 3, 7, 15, 30) AND points IS NULL)
    OR
    (kind = 'points_pack' AND points IN (1000, 3000, 10000, 30000, 66666) AND duration_days IS NULL AND knowledge_index_allowance = 0)
  )
);

CREATE INDEX IF NOT EXISTS idx_billing_catalog_publication
  ON billing_catalog_products(published, kind, duration_days, points);

INSERT INTO billing_catalog_products (
  product_id, catalog_version, kind, display_name, price_cents, points,
  duration_days, knowledge_index_allowance, published, created_at_ms, updated_at_ms
) VALUES
  ('pass-1',       5, 'time_pass',   '1 天会员',     2990,   NULL, 1,  0, TRUE, 1785628800000, 1785628800000),
  ('pass-3',       5, 'time_pass',   '3 天会员',     6990,   NULL, 3,  0, TRUE, 1785628800000, 1785628800000),
  ('pass-7',       5, 'time_pass',   '7 天会员',    12990,   NULL, 7,  0, TRUE, 1785628800000, 1785628800000),
  ('pass-15',      5, 'time_pass',   '15 天会员',   21990,   NULL, 15, 2, TRUE, 1785628800000, 1785628800000),
  ('pass-30',      5, 'time_pass',   '30 天会员',   32990,   NULL, 30, 2, TRUE, 1785628800000, 1785628800000),
  ('points-1000',  5, 'points_pack', '1000 积分',    9990,   1000, NULL, 0, TRUE, 1785628800000, 1785628800000),
  ('points-3000',  5, 'points_pack', '3000 积分',   26990,   3000, NULL, 0, TRUE, 1785628800000, 1785628800000),
  ('points-10000', 5, 'points_pack', '10000 积分',  79990,  10000, NULL, 0, TRUE, 1785628800000, 1785628800000),
  ('points-30000', 5, 'points_pack', '30000 积分', 199990,  30000, NULL, 0, TRUE, 1785628800000, 1785628800000),
  ('points-66666', 5, 'points_pack', '66666 积分', 399990,  66666, NULL, 0, TRUE, 1785628800000, 1785628800000)
ON CONFLICT (product_id) DO NOTHING;
