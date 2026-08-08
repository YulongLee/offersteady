CREATE TABLE IF NOT EXISTS billing_payment_channel_configs (
  channel TEXT PRIMARY KEY CHECK (channel IN ('wechat', 'alipay')),
  enabled BOOLEAN NOT NULL DEFAULT FALSE,
  config_version INTEGER NOT NULL DEFAULT 1 CHECK (config_version > 0),
  public_config JSONB NOT NULL DEFAULT '{}'::jsonb,
  secret_config_ciphertext TEXT,
  validation_status TEXT NOT NULL DEFAULT 'draft' CHECK (validation_status IN ('draft', 'ready', 'error')),
  validation_errors JSONB NOT NULL DEFAULT '[]'::jsonb,
  updated_by_user_id TEXT,
  updated_at_ms BIGINT NOT NULL DEFAULT 0
);

INSERT INTO billing_payment_channel_configs (channel, public_config)
VALUES
  ('wechat', '{"nativeUrl":"https://api.mch.weixin.qq.com/v3/pay/transactions/native"}'::jsonb),
  ('alipay', '{"gatewayUrl":"https://openapi.alipay.com/gateway.do"}'::jsonb)
ON CONFLICT (channel) DO NOTHING;

ALTER TABLE billing_checkout_orders
  DROP CONSTRAINT IF EXISTS billing_checkout_orders_provider_check;
ALTER TABLE billing_checkout_orders
  ADD CONSTRAINT billing_checkout_orders_provider_check
  CHECK (provider IN ('mzfpay', 'alipay', 'wechat'));
