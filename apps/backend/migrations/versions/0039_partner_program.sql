-- Auditable first-level partner commissions. Additive and default-disabled.

ALTER TABLE promotion_links
  ADD COLUMN IF NOT EXISTS link_kind TEXT NOT NULL DEFAULT 'operator';
ALTER TABLE promotion_links
  ADD COLUMN IF NOT EXISTS owner_user_id TEXT NULL REFERENCES auth_users(user_id) ON DELETE SET NULL;
ALTER TABLE promotion_links
  DROP CONSTRAINT IF EXISTS promotion_links_link_kind_check;
ALTER TABLE promotion_links
  ADD CONSTRAINT promotion_links_link_kind_check CHECK (link_kind IN ('operator', 'partner'));
ALTER TABLE promotion_links
  DROP CONSTRAINT IF EXISTS promotion_links_partner_owner_check;
ALTER TABLE promotion_links
  ADD CONSTRAINT promotion_links_partner_owner_check CHECK (
    link_kind = 'partner' OR owner_user_id IS NULL
  );
CREATE UNIQUE INDEX IF NOT EXISTS idx_promotion_links_partner_owner
  ON promotion_links(owner_user_id) WHERE link_kind = 'partner' AND owner_user_id IS NOT NULL;

INSERT INTO promotion_channels (
  channel_id, code, name, sort_order, status, is_system, created_at_ms, updated_at_ms
) VALUES ('promotion-channel-partner', 'partner', '合作伙伴', 800, 'active', TRUE, 0, 0)
ON CONFLICT (code) DO NOTHING;

CREATE TABLE IF NOT EXISTS partner_profiles (
  profile_id TEXT PRIMARY KEY,
  user_id TEXT NOT NULL UNIQUE REFERENCES auth_users(user_id) ON DELETE CASCADE,
  promotion_link_id TEXT NOT NULL UNIQUE REFERENCES promotion_links(link_id),
  status TEXT NOT NULL CHECK (status IN ('active', 'suspended', 'closed')),
  agreement_version TEXT NOT NULL,
  joined_at_ms BIGINT NOT NULL,
  updated_at_ms BIGINT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_partner_profiles_status_joined
  ON partner_profiles(status, joined_at_ms DESC);

CREATE TABLE IF NOT EXISTS growth_acquisition_reward_claims (
  acquired_user_id TEXT PRIMARY KEY REFERENCES auth_users(user_id) ON DELETE CASCADE,
  reward_program TEXT NOT NULL CHECK (reward_program IN ('points_referral', 'cash_partner')),
  partner_user_id TEXT NULL REFERENCES auth_users(user_id) ON DELETE SET NULL,
  referral_activation_id TEXT NULL,
  source_link_id TEXT NULL REFERENCES promotion_links(link_id) ON DELETE SET NULL,
  claimed_at_ms BIGINT NOT NULL,
  CHECK (
    (reward_program = 'cash_partner' AND source_link_id IS NOT NULL AND referral_activation_id IS NULL) OR
    (reward_program = 'points_referral' AND referral_activation_id IS NOT NULL AND partner_user_id IS NULL AND source_link_id IS NULL)
  )
);

CREATE INDEX IF NOT EXISTS idx_growth_reward_claims_partner
  ON growth_acquisition_reward_claims(partner_user_id, claimed_at_ms DESC)
  WHERE reward_program = 'cash_partner';

CREATE TABLE IF NOT EXISTS partner_commission_ledger (
  ledger_entry_id TEXT PRIMARY KEY,
  partner_user_id TEXT NOT NULL,
  entry_type TEXT NOT NULL CHECK (entry_type IN ('earning', 'refund_reversal', 'payout_reserve', 'payout_release', 'payout_paid')),
  source_type TEXT NOT NULL CHECK (source_type IN ('paid_order', 'refund', 'payout')),
  source_id TEXT NOT NULL,
  rule_version INTEGER NOT NULL CHECK (rule_version > 0),
  amount_cents BIGINT NOT NULL CHECK (amount_cents <> 0),
  gross_amount_cents BIGINT NULL CHECK (gross_amount_cents IS NULL OR gross_amount_cents >= 0),
  commission_rate_bps INTEGER NULL CHECK (commission_rate_bps IS NULL OR commission_rate_bps BETWEEN 1 AND 10000),
  hold_days INTEGER NULL CHECK (hold_days IS NULL OR hold_days BETWEEN 0 AND 365),
  eligible_at_ms BIGINT NULL,
  occurred_at_ms BIGINT NOT NULL,
  created_at_ms BIGINT NOT NULL,
  metadata_json JSONB NOT NULL DEFAULT '{}'::jsonb,
  UNIQUE(entry_type, source_type, source_id, rule_version),
  CHECK (
    (entry_type IN ('earning', 'payout_release', 'payout_paid') AND amount_cents > 0) OR
    (entry_type IN ('refund_reversal', 'payout_reserve') AND amount_cents < 0)
  )
);

CREATE INDEX IF NOT EXISTS idx_partner_commission_partner_time
  ON partner_commission_ledger(partner_user_id, occurred_at_ms DESC);
CREATE INDEX IF NOT EXISTS idx_partner_commission_eligibility
  ON partner_commission_ledger(entry_type, eligible_at_ms)
  WHERE entry_type = 'earning';

CREATE OR REPLACE FUNCTION prevent_partner_ledger_mutation()
RETURNS trigger AS $$
BEGIN
  IF TG_OP = 'UPDATE' AND NEW.partner_user_id LIKE 'deleted:%' AND OLD.partner_user_id NOT LIKE 'deleted:%'
     AND (to_jsonb(NEW) - 'partner_user_id') = (to_jsonb(OLD) - 'partner_user_id') THEN
    RETURN NEW;
  END IF;
  RAISE EXCEPTION 'partner commission ledger is append-only';
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trg_partner_ledger_append_only ON partner_commission_ledger;
CREATE TRIGGER trg_partner_ledger_append_only
BEFORE UPDATE OR DELETE ON partner_commission_ledger
FOR EACH ROW EXECUTE FUNCTION prevent_partner_ledger_mutation();

CREATE TABLE IF NOT EXISTS partner_payout_requests (
  payout_request_id TEXT PRIMARY KEY,
  partner_user_id TEXT NOT NULL,
  period_key TEXT NOT NULL CHECK (period_key ~ '^[0-9]{4}-[0-9]{2}$'),
  amount_cents BIGINT NOT NULL CHECK (amount_cents > 0),
  status TEXT NOT NULL CHECK (status IN ('requested', 'approved', 'rejected', 'paid')),
  requested_at_ms BIGINT NOT NULL,
  reviewed_at_ms BIGINT NULL,
  reviewed_by_user_id TEXT NULL,
  paid_at_ms BIGINT NULL,
  payment_reference TEXT NULL,
  decision_reason TEXT NULL,
  updated_at_ms BIGINT NOT NULL,
  UNIQUE(partner_user_id, period_key)
);

CREATE INDEX IF NOT EXISTS idx_partner_payout_status_time
  ON partner_payout_requests(status, requested_at_ms DESC);

CREATE OR REPLACE FUNCTION detach_partner_links_on_account_delete()
RETURNS trigger AS $$
BEGIN
  UPDATE promotion_links SET status='inactive', updated_at_ms=(EXTRACT(EPOCH FROM clock_timestamp()) * 1000)::BIGINT
   WHERE owner_user_id=OLD.user_id AND link_kind='partner';
  UPDATE partner_commission_ledger SET partner_user_id='deleted:' || COALESCE(
    (SELECT profile_id FROM partner_profiles WHERE user_id=OLD.user_id), md5(OLD.user_id)
  ) WHERE partner_user_id=OLD.user_id;
  UPDATE partner_payout_requests SET partner_user_id='deleted:' || COALESCE(
    (SELECT profile_id FROM partner_profiles WHERE user_id=OLD.user_id), md5(OLD.user_id)
  ) WHERE partner_user_id=OLD.user_id;
  RETURN OLD;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trg_auth_user_partner_link_detach ON auth_users;
CREATE TRIGGER trg_auth_user_partner_link_detach
BEFORE DELETE ON auth_users
FOR EACH ROW EXECUTE FUNCTION detach_partner_links_on_account_delete();
