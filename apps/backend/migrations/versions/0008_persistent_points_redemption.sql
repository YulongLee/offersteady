-- Durable globally single-use points redemption.
-- Plaintext bearer codes are intentionally never persisted.

CREATE TABLE IF NOT EXISTS points_redemption_codes (
  code_digest TEXT PRIMARY KEY,
  public_hint TEXT NOT NULL,
  points INTEGER NOT NULL CHECK (points > 0),
  status TEXT NOT NULL CHECK (status IN ('active', 'redeemed', 'disabled')),
  redeemed_by_user_id TEXT NULL,
  redeemed_at_ms BIGINT NULL,
  redemption_id TEXT NULL UNIQUE,
  created_at_ms BIGINT NOT NULL,
  updated_at_ms BIGINT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_points_redemption_codes_status
  ON points_redemption_codes(status);

CREATE TABLE IF NOT EXISTS points_redemption_ledger (
  ledger_entry_id TEXT PRIMARY KEY,
  user_id TEXT NOT NULL,
  kind TEXT NOT NULL CHECK (kind = 'redemption_credit'),
  points INTEGER NOT NULL CHECK (points > 0),
  created_at_ms BIGINT NOT NULL,
  reference_id TEXT NOT NULL UNIQUE,
  description TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_points_redemption_ledger_user_created
  ON points_redemption_ledger(user_id, created_at_ms DESC);

CREATE TABLE IF NOT EXISTS points_redemptions (
  redemption_id TEXT PRIMARY KEY,
  code_digest TEXT NOT NULL UNIQUE REFERENCES points_redemption_codes(code_digest),
  user_id TEXT NOT NULL,
  idempotency_key TEXT NOT NULL,
  points INTEGER NOT NULL CHECK (points > 0),
  persisted_balance INTEGER NOT NULL CHECK (persisted_balance >= 0),
  public_hint TEXT NOT NULL,
  redeemed_at_ms BIGINT NOT NULL,
  ledger_entry_id TEXT NOT NULL UNIQUE REFERENCES points_redemption_ledger(ledger_entry_id),
  UNIQUE(user_id, idempotency_key)
);

CREATE INDEX IF NOT EXISTS idx_points_redemptions_user_created
  ON points_redemptions(user_id, redeemed_at_ms DESC);

CREATE OR REPLACE FUNCTION prevent_points_redemption_ledger_mutation()
RETURNS trigger AS $$
BEGIN
  RAISE EXCEPTION 'points redemption ledger is immutable';
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trg_points_redemption_ledger_immutable ON points_redemption_ledger;
CREATE TRIGGER trg_points_redemption_ledger_immutable
BEFORE UPDATE OR DELETE ON points_redemption_ledger
FOR EACH ROW EXECUTE FUNCTION prevent_points_redemption_ledger_mutation();
