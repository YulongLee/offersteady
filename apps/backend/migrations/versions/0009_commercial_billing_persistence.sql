-- Durable commercial wallet, checkout, entitlement, and knowledge-index billing state.

ALTER TABLE points_redemption_ledger
  DROP CONSTRAINT IF EXISTS points_redemption_ledger_kind_check;
ALTER TABLE points_redemption_ledger
  DROP CONSTRAINT IF EXISTS points_redemption_ledger_points_check;
ALTER TABLE points_redemption_ledger
  ADD CONSTRAINT points_redemption_ledger_kind_check CHECK (
    kind IN (
      'welcome_grant', 'redemption_credit', 'purchase_credit',
      'knowledge_index_settlement', 'redemption_reversal'
    )
  );
ALTER TABLE points_redemption_ledger
  ADD CONSTRAINT points_redemption_ledger_points_check CHECK (
    (kind IN ('welcome_grant', 'redemption_credit', 'purchase_credit') AND points > 0)
    OR (kind IN ('knowledge_index_settlement', 'redemption_reversal') AND points < 0)
  );

CREATE TABLE IF NOT EXISTS billing_checkout_orders (
  order_id TEXT PRIMARY KEY,
  user_id TEXT NOT NULL,
  idempotency_key TEXT NOT NULL,
  product_snapshot JSONB NOT NULL,
  amount_cents INTEGER NOT NULL CHECK (amount_cents > 0),
  currency TEXT NOT NULL,
  channel TEXT NOT NULL CHECK (channel IN ('wechat', 'alipay')),
  status TEXT NOT NULL CHECK (status IN ('payment_pending', 'paid', 'failed')),
  action JSONB NOT NULL,
  provider_trade_no TEXT NULL,
  created_at_ms BIGINT NOT NULL,
  updated_at_ms BIGINT NOT NULL,
  paid_at_ms BIGINT NULL,
  UNIQUE(user_id, idempotency_key)
);

CREATE INDEX IF NOT EXISTS idx_billing_checkout_orders_user_created
  ON billing_checkout_orders(user_id, created_at_ms DESC);

CREATE UNIQUE INDEX IF NOT EXISTS idx_billing_checkout_provider_trade_no
  ON billing_checkout_orders(provider_trade_no)
  WHERE provider_trade_no IS NOT NULL;

CREATE TABLE IF NOT EXISTS billing_time_pass_entitlements (
  entitlement_id TEXT PRIMARY KEY,
  user_id TEXT NOT NULL,
  product_id TEXT NOT NULL,
  starts_at_ms BIGINT NOT NULL,
  ends_at_ms BIGINT NOT NULL,
  order_id TEXT NOT NULL UNIQUE REFERENCES billing_checkout_orders(order_id),
  knowledge_allowance_granted INTEGER NOT NULL DEFAULT 0 CHECK (knowledge_allowance_granted >= 0),
  knowledge_allowance_used INTEGER NOT NULL DEFAULT 0 CHECK (knowledge_allowance_used >= 0),
  knowledge_allowance_locked INTEGER NOT NULL DEFAULT 0 CHECK (knowledge_allowance_locked >= 0)
);

CREATE INDEX IF NOT EXISTS idx_billing_entitlements_user_time
  ON billing_time_pass_entitlements(user_id, starts_at_ms, ends_at_ms);

CREATE TABLE IF NOT EXISTS billing_index_quotes (
  quote_id TEXT PRIMARY KEY,
  user_id TEXT NOT NULL,
  idempotency_key TEXT NOT NULL,
  document_version_id TEXT NOT NULL,
  token_estimate INTEGER NOT NULL CHECK (token_estimate > 0),
  catalog_version INTEGER NOT NULL,
  tokenizer_version TEXT NOT NULL,
  points_required INTEGER NOT NULL CHECK (points_required > 0),
  projected_balance INTEGER NOT NULL,
  created_at_ms BIGINT NOT NULL,
  UNIQUE(user_id, idempotency_key)
);

CREATE TABLE IF NOT EXISTS billing_index_reservations (
  reservation_id TEXT PRIMARY KEY,
  quote_id TEXT NOT NULL UNIQUE REFERENCES billing_index_quotes(quote_id),
  user_id TEXT NOT NULL,
  document_version_id TEXT NOT NULL,
  points_reserved INTEGER NOT NULL CHECK (points_reserved > 0),
  status TEXT NOT NULL CHECK (status IN ('reserved', 'settled', 'released')),
  created_at_ms BIGINT NOT NULL,
  settled_at_ms BIGINT NULL,
  released_at_ms BIGINT NULL
);

CREATE INDEX IF NOT EXISTS idx_billing_index_reservations_user_status
  ON billing_index_reservations(user_id, status);

