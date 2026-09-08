-- Global-only encrypted Creem configuration. Test and Live remain separate rows.
ALTER TABLE global_commerce_provider_configs
  ADD COLUMN IF NOT EXISTS credential_ciphertext TEXT NULL;

ALTER TABLE global_commerce_provider_configs
  ADD COLUMN IF NOT EXISTS connection_checked_at_ms BIGINT NULL;

