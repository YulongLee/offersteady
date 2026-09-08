-- Isolated Global commerce schema. Chinese-edition runtime never reads these tables.

CREATE TABLE IF NOT EXISTS global_commerce_plan_versions (
  offer_code TEXT NOT NULL CHECK (offer_code IN (
    'global-free','global-interview-pass','global-pro-weekly','global-pro-monthly','global-job-hunt'
  )),
  plan_version INTEGER NOT NULL CHECK (plan_version > 0),
  display_name TEXT NOT NULL CHECK (CHAR_LENGTH(display_name) BETWEEN 2 AND 80),
  description TEXT NOT NULL CHECK (CHAR_LENGTH(description) BETWEEN 2 AND 300),
  currency TEXT NOT NULL DEFAULT 'USD' CHECK (currency = 'USD'),
  price_cents INTEGER NOT NULL CHECK (price_cents >= 0),
  billing_mode TEXT NOT NULL CHECK (billing_mode IN ('free','one_time','recurring')),
  duration_days INTEGER NULL CHECK (duration_days IS NULL OR duration_days BETWEEN 1 AND 366),
  copilot_minutes INTEGER NULL CHECK (copilot_minutes IS NULL OR copilot_minutes > 0),
  screen_assist_uses INTEGER NULL CHECK (screen_assist_uses IS NULL OR screen_assist_uses > 0),
  resume_jd_enabled BOOLEAN NOT NULL DEFAULT FALSE,
  knowledge_base_enabled BOOLEAN NOT NULL DEFAULT FALSE,
  written_exam_enabled BOOLEAN NOT NULL DEFAULT FALSE,
  full_product_enabled BOOLEAN NOT NULL DEFAULT FALSE,
  status TEXT NOT NULL DEFAULT 'draft' CHECK (status IN ('draft','active','retired')),
  featured BOOLEAN NOT NULL DEFAULT FALSE,
  display_order INTEGER NOT NULL CHECK (display_order >= 0),
  created_by_user_id TEXT NULL,
  created_at_ms BIGINT NOT NULL,
  PRIMARY KEY (offer_code, plan_version),
  CHECK ((billing_mode = 'free' AND price_cents = 0) OR (billing_mode <> 'free' AND price_cents > 0)),
  CHECK ((billing_mode = 'recurring' AND offer_code = 'global-pro-monthly') OR billing_mode <> 'recurring')
);

CREATE UNIQUE INDEX IF NOT EXISTS idx_global_commerce_one_active_plan
  ON global_commerce_plan_versions(offer_code) WHERE status = 'active';
CREATE INDEX IF NOT EXISTS idx_global_commerce_plan_display
  ON global_commerce_plan_versions(status, display_order, offer_code);

CREATE TABLE IF NOT EXISTS global_commerce_provider_configs (
  mode TEXT PRIMARY KEY CHECK (mode IN ('test','live')),
  provider TEXT NOT NULL DEFAULT 'creem' CHECK (provider = 'creem'),
  enabled BOOLEAN NOT NULL DEFAULT FALSE,
  config_version INTEGER NOT NULL DEFAULT 1 CHECK (config_version > 0),
  api_key_fingerprint TEXT NULL,
  webhook_secret_fingerprint TEXT NULL,
  webhook_url TEXT NULL,
  fair_use_policy_url TEXT NULL,
  refund_policy_url TEXT NULL,
  terms_url TEXT NULL,
  privacy_url TEXT NULL,
  validation_status TEXT NOT NULL DEFAULT 'draft' CHECK (validation_status IN ('draft','ready','error')),
  validation_errors JSONB NOT NULL DEFAULT '[]'::jsonb,
  webhook_accepted_at_ms BIGINT NULL,
  updated_by_user_id TEXT NULL,
  updated_at_ms BIGINT NOT NULL DEFAULT 0
);

INSERT INTO global_commerce_provider_configs(mode) VALUES ('test'),('live')
ON CONFLICT (mode) DO NOTHING;

CREATE TABLE IF NOT EXISTS global_commerce_product_mappings (
  mode TEXT NOT NULL CHECK (mode IN ('test','live')),
  offer_code TEXT NOT NULL,
  plan_version INTEGER NOT NULL,
  provider_product_id TEXT NOT NULL CHECK (CHAR_LENGTH(provider_product_id) BETWEEN 6 AND 160),
  validation_status TEXT NOT NULL DEFAULT 'draft' CHECK (validation_status IN ('draft','ready','error')),
  validated_amount_cents INTEGER NULL,
  validated_currency TEXT NULL,
  validated_billing_mode TEXT NULL,
  validated_at_ms BIGINT NULL,
  updated_by_user_id TEXT NULL,
  updated_at_ms BIGINT NOT NULL,
  PRIMARY KEY (mode, offer_code),
  UNIQUE (mode, provider_product_id),
  FOREIGN KEY (offer_code, plan_version)
    REFERENCES global_commerce_plan_versions(offer_code, plan_version)
);

CREATE TABLE IF NOT EXISTS global_commerce_orders (
  order_id TEXT PRIMARY KEY,
  user_id TEXT NOT NULL,
  offer_code TEXT NOT NULL,
  plan_version INTEGER NOT NULL,
  mode TEXT NOT NULL CHECK (mode IN ('test','live')),
  provider TEXT NOT NULL DEFAULT 'creem' CHECK (provider = 'creem'),
  expected_amount_cents INTEGER NOT NULL CHECK (expected_amount_cents > 0),
  expected_currency TEXT NOT NULL DEFAULT 'USD' CHECK (expected_currency = 'USD'),
  status TEXT NOT NULL CHECK (status IN (
    'pending','checkout_created','confirming','paid','failed','expired','refunded','disputed'
  )),
  idempotency_key TEXT NOT NULL CHECK (CHAR_LENGTH(idempotency_key) BETWEEN 8 AND 128),
  checkout_url TEXT NULL,
  provider_checkout_id TEXT NULL,
  provider_order_id TEXT NULL,
  provider_subscription_id TEXT NULL,
  provider_customer_id TEXT NULL,
  customer_email_hash TEXT NULL,
  provider_fee_cents INTEGER NULL,
  provider_tax_cents INTEGER NULL,
  failure_code TEXT NULL,
  reconciliation_required BOOLEAN NOT NULL DEFAULT FALSE,
  created_at_ms BIGINT NOT NULL,
  updated_at_ms BIGINT NOT NULL,
  paid_at_ms BIGINT NULL,
  refunded_at_ms BIGINT NULL,
  disputed_at_ms BIGINT NULL,
  UNIQUE (user_id, idempotency_key),
  UNIQUE (mode, provider_checkout_id),
  UNIQUE (mode, provider_order_id),
  FOREIGN KEY (offer_code, plan_version)
    REFERENCES global_commerce_plan_versions(offer_code, plan_version)
);

CREATE INDEX IF NOT EXISTS idx_global_commerce_orders_user_created
  ON global_commerce_orders(user_id, created_at_ms DESC);
CREATE INDEX IF NOT EXISTS idx_global_commerce_orders_reconciliation
  ON global_commerce_orders(status, updated_at_ms) WHERE reconciliation_required = TRUE;

CREATE TABLE IF NOT EXISTS global_commerce_provider_events (
  mode TEXT NOT NULL CHECK (mode IN ('test','live')),
  provider_event_id TEXT NOT NULL,
  event_type TEXT NOT NULL,
  provider_created_at_ms BIGINT NOT NULL,
  payload_sha256 TEXT NOT NULL CHECK (CHAR_LENGTH(payload_sha256) = 64),
  status TEXT NOT NULL CHECK (status IN ('processing','processed','ignored','failed')),
  order_id TEXT NULL,
  provider_subscription_id TEXT NULL,
  error_code TEXT NULL,
  received_at_ms BIGINT NOT NULL,
  processed_at_ms BIGINT NULL,
  PRIMARY KEY (mode, provider_event_id)
);

CREATE INDEX IF NOT EXISTS idx_global_commerce_events_received
  ON global_commerce_provider_events(received_at_ms DESC);

CREATE TABLE IF NOT EXISTS global_commerce_subscriptions (
  subscription_id TEXT PRIMARY KEY,
  user_id TEXT NOT NULL,
  offer_code TEXT NOT NULL CHECK (offer_code = 'global-pro-monthly'),
  plan_version INTEGER NOT NULL,
  mode TEXT NOT NULL CHECK (mode IN ('test','live')),
  provider_subscription_id TEXT NOT NULL,
  provider_customer_id TEXT NOT NULL,
  status TEXT NOT NULL CHECK (status IN ('active','canceling','canceled','paused','expired')),
  current_period_start_ms BIGINT NOT NULL,
  current_period_end_ms BIGINT NOT NULL,
  canceled_at_ms BIGINT NULL,
  provider_updated_at_ms BIGINT NOT NULL,
  created_at_ms BIGINT NOT NULL,
  updated_at_ms BIGINT NOT NULL,
  UNIQUE (mode, provider_subscription_id),
  FOREIGN KEY (offer_code, plan_version)
    REFERENCES global_commerce_plan_versions(offer_code, plan_version)
);

CREATE TABLE IF NOT EXISTS global_commerce_entitlements (
  entitlement_id TEXT PRIMARY KEY,
  user_id TEXT NOT NULL,
  offer_code TEXT NOT NULL,
  plan_version INTEGER NOT NULL,
  source_kind TEXT NOT NULL CHECK (source_kind IN ('free_grant','order','subscription_period','admin')),
  source_id TEXT NOT NULL,
  status TEXT NOT NULL CHECK (status IN ('active','exhausted','expired','revoked')),
  starts_at_ms BIGINT NOT NULL,
  ends_at_ms BIGINT NULL,
  copilot_minutes_granted INTEGER NULL,
  copilot_minutes_used INTEGER NOT NULL DEFAULT 0 CHECK (copilot_minutes_used >= 0),
  copilot_minutes_locked INTEGER NOT NULL DEFAULT 0 CHECK (copilot_minutes_locked >= 0),
  screen_assist_uses_granted INTEGER NULL,
  screen_assist_uses_used INTEGER NOT NULL DEFAULT 0 CHECK (screen_assist_uses_used >= 0),
  screen_assist_uses_locked INTEGER NOT NULL DEFAULT 0 CHECK (screen_assist_uses_locked >= 0),
  resume_jd_enabled BOOLEAN NOT NULL,
  knowledge_base_enabled BOOLEAN NOT NULL,
  written_exam_enabled BOOLEAN NOT NULL,
  full_product_enabled BOOLEAN NOT NULL,
  created_at_ms BIGINT NOT NULL,
  updated_at_ms BIGINT NOT NULL,
  UNIQUE (source_kind, source_id),
  FOREIGN KEY (offer_code, plan_version)
    REFERENCES global_commerce_plan_versions(offer_code, plan_version)
);

CREATE INDEX IF NOT EXISTS idx_global_commerce_entitlements_user_active
  ON global_commerce_entitlements(user_id, status, starts_at_ms, ends_at_ms);

CREATE TABLE IF NOT EXISTS global_commerce_free_grants (
  user_id TEXT NOT NULL,
  grant_kind TEXT NOT NULL DEFAULT 'initial' CHECK (grant_kind = 'initial'),
  entitlement_id TEXT NOT NULL UNIQUE REFERENCES global_commerce_entitlements(entitlement_id),
  granted_at_ms BIGINT NOT NULL,
  PRIMARY KEY (user_id, grant_kind)
);

CREATE TABLE IF NOT EXISTS global_commerce_usage_reservations (
  operation_id TEXT PRIMARY KEY,
  user_id TEXT NOT NULL,
  entitlement_id TEXT NOT NULL REFERENCES global_commerce_entitlements(entitlement_id),
  usage_kind TEXT NOT NULL CHECK (usage_kind IN ('copilot_minute','screen_assist')),
  amount INTEGER NOT NULL CHECK (amount > 0),
  status TEXT NOT NULL CHECK (status IN ('reserved','settled','released')),
  created_at_ms BIGINT NOT NULL,
  settled_at_ms BIGINT NULL,
  released_at_ms BIGINT NULL
);

CREATE INDEX IF NOT EXISTS idx_global_commerce_usage_stale
  ON global_commerce_usage_reservations(status, created_at_ms) WHERE status = 'reserved';

CREATE TABLE IF NOT EXISTS global_commerce_fair_use_decisions (
  decision_id TEXT PRIMARY KEY,
  user_id TEXT NOT NULL,
  status TEXT NOT NULL CHECK (status IN ('review','restricted','cleared','expired')),
  reason_code TEXT NOT NULL,
  evidence JSONB NOT NULL DEFAULT '{}'::jsonb,
  restrict_new_sessions BOOLEAN NOT NULL DEFAULT FALSE,
  effective_at_ms BIGINT NOT NULL,
  expires_at_ms BIGINT NULL,
  reviewed_by_user_id TEXT NULL,
  review_note TEXT NULL,
  created_at_ms BIGINT NOT NULL,
  updated_at_ms BIGINT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_global_commerce_fair_use_active
  ON global_commerce_fair_use_decisions(user_id, status, effective_at_ms DESC);

-- The seed is immutable version 1. Later operator changes insert a new version.
INSERT INTO global_commerce_plan_versions (
  offer_code, plan_version, display_name, description, currency, price_cents,
  billing_mode, duration_days, copilot_minutes, screen_assist_uses,
  resume_jd_enabled, knowledge_base_enabled, written_exam_enabled,
  full_product_enabled, status, featured, display_order, created_at_ms
) VALUES
  ('global-free', 1, 'Free', 'Try OfferSteady without a card.', 'USD', 0,
   'free', NULL, 15, 3, FALSE, FALSE, FALSE, FALSE, 'active', FALSE, 0, 1788537600000),
  ('global-interview-pass', 1, 'Interview Pass', 'Focused access for one or two interviews.', 'USD', 999,
   'one_time', 7, 180, NULL, TRUE, FALSE, TRUE, FALSE, 'active', FALSE, 1, 1788537600000),
  ('global-pro-weekly', 1, 'Pro Weekly', 'Unlimited full-product access for interview week.', 'USD', 1999,
   'one_time', 7, NULL, NULL, TRUE, TRUE, TRUE, TRUE, 'active', TRUE, 2, 1788537600000),
  ('global-pro-monthly', 1, 'Pro Monthly', 'Unlimited full-product access with monthly renewal.', 'USD', 3999,
   'recurring', 30, NULL, NULL, TRUE, TRUE, TRUE, TRUE, 'active', FALSE, 3, 1788537600000),
  ('global-job-hunt', 1, 'Job Hunt', 'Unlimited full-product access for a focused job search.', 'USD', 7999,
   'one_time', 90, NULL, NULL, TRUE, TRUE, TRUE, TRUE, 'active', FALSE, 4, 1788537600000)
ON CONFLICT (offer_code, plan_version) DO NOTHING;
