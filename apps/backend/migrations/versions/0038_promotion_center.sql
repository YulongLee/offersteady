-- First-party promotion attribution and aggregate reporting.
-- Additive only: existing product facts remain authoritative and no hot-path table is altered.

CREATE TABLE IF NOT EXISTS promotion_channels (
  channel_id TEXT PRIMARY KEY,
  code TEXT NOT NULL UNIQUE,
  name TEXT NOT NULL,
  sort_order INTEGER NOT NULL DEFAULT 0,
  status TEXT NOT NULL CHECK (status IN ('active', 'inactive')),
  is_system BOOLEAN NOT NULL DEFAULT FALSE,
  created_by_user_id TEXT NULL,
  created_at_ms BIGINT NOT NULL,
  updated_at_ms BIGINT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_promotion_channels_status_order
  ON promotion_channels(status, sort_order, created_at_ms);

CREATE TABLE IF NOT EXISTS promotion_campaigns (
  campaign_id TEXT PRIMARY KEY,
  name TEXT NOT NULL,
  objective TEXT NOT NULL DEFAULT '',
  status TEXT NOT NULL CHECK (status IN ('draft', 'active', 'paused', 'ended')),
  starts_at_ms BIGINT NULL,
  ends_at_ms BIGINT NULL,
  budget_cents BIGINT NULL CHECK (budget_cents IS NULL OR budget_cents >= 0),
  notes TEXT NOT NULL DEFAULT '',
  created_by_user_id TEXT NULL,
  created_at_ms BIGINT NOT NULL,
  updated_at_ms BIGINT NOT NULL,
  CHECK (ends_at_ms IS NULL OR starts_at_ms IS NULL OR ends_at_ms > starts_at_ms)
);

CREATE INDEX IF NOT EXISTS idx_promotion_campaigns_status_period
  ON promotion_campaigns(status, starts_at_ms, ends_at_ms);

CREATE TABLE IF NOT EXISTS promotion_links (
  link_id TEXT PRIMARY KEY,
  slug TEXT NOT NULL UNIQUE,
  content_name TEXT NOT NULL,
  channel_id TEXT NOT NULL REFERENCES promotion_channels(channel_id),
  campaign_id TEXT NULL REFERENCES promotion_campaigns(campaign_id),
  destination_path TEXT NOT NULL,
  status TEXT NOT NULL CHECK (status IN ('active', 'inactive')),
  starts_at_ms BIGINT NULL,
  ends_at_ms BIGINT NULL,
  attribution_locked_at_ms BIGINT NULL,
  cloned_from_link_id TEXT NULL REFERENCES promotion_links(link_id),
  created_by_user_id TEXT NULL,
  created_at_ms BIGINT NOT NULL,
  updated_at_ms BIGINT NOT NULL,
  CHECK (destination_path ~ '^/[A-Za-z0-9/_?&=.%+-]*$'),
  CHECK (destination_path !~ E'[\\r\\n]'),
  CHECK (ends_at_ms IS NULL OR starts_at_ms IS NULL OR ends_at_ms > starts_at_ms)
);

CREATE INDEX IF NOT EXISTS idx_promotion_links_dimensions
  ON promotion_links(channel_id, campaign_id, status, created_at_ms DESC);
CREATE INDEX IF NOT EXISTS idx_promotion_links_active_period
  ON promotion_links(status, starts_at_ms, ends_at_ms);

CREATE OR REPLACE FUNCTION prevent_used_promotion_link_reclassification()
RETURNS trigger AS $$
BEGIN
  IF OLD.attribution_locked_at_ms IS NOT NULL AND
     (NEW.channel_id IS DISTINCT FROM OLD.channel_id OR NEW.campaign_id IS DISTINCT FROM OLD.campaign_id) THEN
    RAISE EXCEPTION 'used promotion link attribution is immutable; clone the link instead';
  END IF;
  RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trg_promotion_link_attribution_immutable ON promotion_links;
CREATE TRIGGER trg_promotion_link_attribution_immutable
BEFORE UPDATE ON promotion_links
FOR EACH ROW EXECUTE FUNCTION prevent_used_promotion_link_reclassification();

CREATE TABLE IF NOT EXISTS promotion_cost_entries (
  cost_entry_id TEXT PRIMARY KEY,
  scope_type TEXT NOT NULL CHECK (scope_type IN ('channel', 'campaign', 'link')),
  channel_id TEXT NULL REFERENCES promotion_channels(channel_id),
  campaign_id TEXT NULL REFERENCES promotion_campaigns(campaign_id),
  link_id TEXT NULL REFERENCES promotion_links(link_id),
  cost_date DATE NOT NULL,
  amount_cents BIGINT NOT NULL CHECK (amount_cents <> 0),
  currency TEXT NOT NULL DEFAULT 'CNY' CHECK (currency = 'CNY'),
  reason TEXT NOT NULL,
  reversal_of_entry_id TEXT NULL UNIQUE REFERENCES promotion_cost_entries(cost_entry_id),
  created_by_user_id TEXT NOT NULL,
  created_at_ms BIGINT NOT NULL,
  CHECK (
    (scope_type = 'channel' AND channel_id IS NOT NULL AND campaign_id IS NULL AND link_id IS NULL) OR
    (scope_type = 'campaign' AND channel_id IS NULL AND campaign_id IS NOT NULL AND link_id IS NULL) OR
    (scope_type = 'link' AND channel_id IS NULL AND campaign_id IS NULL AND link_id IS NOT NULL)
  ),
  CHECK (
    (reversal_of_entry_id IS NULL AND amount_cents > 0) OR
    (reversal_of_entry_id IS NOT NULL AND amount_cents < 0)
  )
);

CREATE INDEX IF NOT EXISTS idx_promotion_cost_scope_date
  ON promotion_cost_entries(scope_type, channel_id, campaign_id, link_id, cost_date);

CREATE OR REPLACE FUNCTION prevent_promotion_cost_mutation()
RETURNS trigger AS $$
BEGIN
  RAISE EXCEPTION 'promotion cost entries are append-only';
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trg_promotion_cost_append_only ON promotion_cost_entries;
CREATE TRIGGER trg_promotion_cost_append_only
BEFORE UPDATE OR DELETE ON promotion_cost_entries
FOR EACH ROW EXECUTE FUNCTION prevent_promotion_cost_mutation();

CREATE TABLE IF NOT EXISTS promotion_touchpoints (
  touchpoint_id TEXT PRIMARY KEY,
  event_id TEXT NOT NULL UNIQUE,
  event_type TEXT NOT NULL CHECK (event_type IN ('redirect_hit', 'qualified_visit', 'assist_touch')),
  link_id TEXT NOT NULL REFERENCES promotion_links(link_id),
  visitor_hmac TEXT NULL,
  click_hmac TEXT NULL,
  occurred_at_ms BIGINT NOT NULL,
  destination_key TEXT NOT NULL,
  referrer_host TEXT NULL,
  device_class TEXT NULL CHECK (device_class IS NULL OR device_class IN ('desktop', 'mobile', 'tablet', 'unknown')),
  qualification_state TEXT NOT NULL CHECK (qualification_state IN ('raw', 'qualified', 'excluded', 'anonymous_aggregate')),
  exclusion_reason TEXT NULL,
  created_at_ms BIGINT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_promotion_touchpoints_event_time
  ON promotion_touchpoints(occurred_at_ms DESC, event_type, qualification_state);
CREATE INDEX IF NOT EXISTS idx_promotion_touchpoints_visitor_time
  ON promotion_touchpoints(visitor_hmac, occurred_at_ms DESC) WHERE visitor_hmac IS NOT NULL;
CREATE INDEX IF NOT EXISTS idx_promotion_touchpoints_link_time
  ON promotion_touchpoints(link_id, occurred_at_ms DESC);

CREATE TABLE IF NOT EXISTS promotion_identity_bindings (
  identity_binding_id TEXT PRIMARY KEY,
  claim_key TEXT NOT NULL UNIQUE,
  visitor_hmac TEXT NOT NULL,
  user_id TEXT NULL REFERENCES auth_users(user_id) ON DELETE SET NULL,
  first_touchpoint_id TEXT NULL REFERENCES promotion_touchpoints(touchpoint_id) ON DELETE SET NULL,
  last_non_direct_touchpoint_id TEXT NULL REFERENCES promotion_touchpoints(touchpoint_id) ON DELETE SET NULL,
  first_touch_link_id TEXT NULL REFERENCES promotion_links(link_id),
  last_non_direct_link_id TEXT NULL REFERENCES promotion_links(link_id),
  acquisition_locked_at_ms BIGINT NOT NULL,
  deleted_at_ms BIGINT NULL,
  created_at_ms BIGINT NOT NULL,
  updated_at_ms BIGINT NOT NULL
);

CREATE UNIQUE INDEX IF NOT EXISTS idx_promotion_identity_user_active
  ON promotion_identity_bindings(user_id) WHERE user_id IS NOT NULL AND deleted_at_ms IS NULL;
CREATE INDEX IF NOT EXISTS idx_promotion_identity_visitor
  ON promotion_identity_bindings(visitor_hmac, created_at_ms DESC);

CREATE TABLE IF NOT EXISTS promotion_conversion_events (
  conversion_event_id TEXT PRIMARY KEY,
  event_id TEXT NOT NULL UNIQUE,
  conversion_type TEXT NOT NULL CHECK (conversion_type IN ('download', 'registration', 'use', 'order', 'payment')),
  source_record_id TEXT NOT NULL,
  visitor_hmac TEXT NULL,
  user_id TEXT NULL REFERENCES auth_users(user_id) ON DELETE SET NULL,
  amount_cents BIGINT NULL CHECK (amount_cents IS NULL OR amount_cents >= 0),
  currency TEXT NULL,
  occurred_at_ms BIGINT NOT NULL,
  created_at_ms BIGINT NOT NULL,
  UNIQUE(conversion_type, source_record_id)
);

CREATE INDEX IF NOT EXISTS idx_promotion_conversion_user_time
  ON promotion_conversion_events(user_id, conversion_type, occurred_at_ms DESC);
CREATE INDEX IF NOT EXISTS idx_promotion_conversion_visitor_time
  ON promotion_conversion_events(visitor_hmac, conversion_type, occurred_at_ms DESC);

CREATE OR REPLACE FUNCTION detach_promotion_identity_on_account_delete()
RETURNS trigger AS $$
DECLARE
  deleted_ms BIGINT;
BEGIN
  deleted_ms := (EXTRACT(EPOCH FROM clock_timestamp()) * 1000)::BIGINT;
  UPDATE promotion_identity_bindings
     SET user_id = NULL,
         visitor_hmac = 'deleted:' || identity_binding_id,
         first_touchpoint_id = NULL,
         last_non_direct_touchpoint_id = NULL,
         first_touch_link_id = NULL,
         last_non_direct_link_id = NULL,
         deleted_at_ms = deleted_ms,
         updated_at_ms = deleted_ms
   WHERE user_id = OLD.user_id;
  UPDATE promotion_conversion_events
     SET user_id = NULL, visitor_hmac = NULL
   WHERE user_id = OLD.user_id;
  RETURN OLD;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trg_auth_user_promotion_detach ON auth_users;
CREATE TRIGGER trg_auth_user_promotion_detach
BEFORE DELETE ON auth_users
FOR EACH ROW EXECUTE FUNCTION detach_promotion_identity_on_account_delete();

CREATE TABLE IF NOT EXISTS promotion_attribution_facts (
  attribution_fact_id TEXT PRIMARY KEY,
  conversion_type TEXT NOT NULL,
  source_record_id TEXT NOT NULL,
  attribution_model TEXT NOT NULL CHECK (attribution_model IN ('first_touch', 'last_non_direct_touch')),
  model_version INTEGER NOT NULL CHECK (model_version > 0),
  channel_id TEXT NULL REFERENCES promotion_channels(channel_id),
  campaign_id TEXT NULL REFERENCES promotion_campaigns(campaign_id),
  link_id TEXT NULL REFERENCES promotion_links(link_id),
  bucket_code TEXT NULL CHECK (bucket_code IS NULL OR bucket_code IN ('direct', 'organic', 'unattributed')),
  amount_cents BIGINT NULL CHECK (amount_cents IS NULL OR amount_cents >= 0),
  occurred_at_ms BIGINT NOT NULL,
  computed_at_ms BIGINT NOT NULL,
  UNIQUE(conversion_type, source_record_id, attribution_model, model_version)
);

CREATE INDEX IF NOT EXISTS idx_promotion_attribution_paid_dimensions
  ON promotion_attribution_facts(attribution_model, model_version, occurred_at_ms, channel_id, campaign_id, link_id)
  WHERE conversion_type = 'payment';

CREATE TABLE IF NOT EXISTS promotion_metric_snapshots (
  bucket_date DATE NOT NULL,
  attribution_model TEXT NOT NULL,
  model_version INTEGER NOT NULL,
  dimension_type TEXT NOT NULL CHECK (dimension_type IN ('overview', 'channel', 'campaign', 'link', 'bucket')),
  dimension_id TEXT NOT NULL,
  metrics_json JSONB NOT NULL,
  coverage_json JSONB NOT NULL,
  computed_at_ms BIGINT NOT NULL,
  PRIMARY KEY (bucket_date, attribution_model, model_version, dimension_type, dimension_id)
);

CREATE INDEX IF NOT EXISTS idx_promotion_snapshots_dimension_date
  ON promotion_metric_snapshots(dimension_type, dimension_id, attribution_model, model_version, bucket_date DESC);

CREATE TABLE IF NOT EXISTS promotion_analytics_runs (
  run_id TEXT PRIMARY KEY,
  run_kind TEXT NOT NULL CHECK (run_kind IN ('scheduled', 'backfill', 'repair', 'manual', 'retention', 'reconciliation')),
  status TEXT NOT NULL CHECK (status IN ('running', 'completed', 'failed', 'skipped')),
  range_started_at_ms BIGINT NOT NULL,
  range_ended_at_ms BIGINT NOT NULL,
  processed_count BIGINT NOT NULL DEFAULT 0,
  mismatch_count BIGINT NOT NULL DEFAULT 0,
  safe_error_code TEXT NULL,
  started_at_ms BIGINT NOT NULL,
  completed_at_ms BIGINT NULL
);

CREATE INDEX IF NOT EXISTS idx_promotion_analytics_runs_started
  ON promotion_analytics_runs(started_at_ms DESC);

INSERT INTO promotion_channels (
  channel_id, code, name, sort_order, status, is_system, created_at_ms, updated_at_ms
) VALUES
  ('promotion-channel-direct', 'direct', '直接访问', 900, 'active', TRUE, 0, 0),
  ('promotion-channel-organic', 'organic', '自然流量', 901, 'active', TRUE, 0, 0),
  ('promotion-channel-unattributed', 'unattributed', '未归因', 902, 'active', TRUE, 0, 0)
ON CONFLICT (code) DO NOTHING;
