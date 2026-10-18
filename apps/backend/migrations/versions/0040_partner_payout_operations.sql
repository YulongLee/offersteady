-- Versioned, encrypted payout details for manual partner settlements.

CREATE TABLE IF NOT EXISTS partner_payout_profiles (
  payout_profile_id TEXT PRIMARY KEY,
  partner_user_id TEXT NOT NULL,
  version INTEGER NOT NULL CHECK (version > 0),
  payout_method TEXT NOT NULL CHECK (payout_method IN ('alipay', 'wechat')),
  account_name_ciphertext TEXT NOT NULL,
  account_identifier_ciphertext TEXT NOT NULL,
  masked_account_name TEXT NOT NULL,
  masked_account_identifier TEXT NOT NULL,
  key_version INTEGER NOT NULL CHECK (key_version > 0),
  status TEXT NOT NULL CHECK (status IN ('current', 'superseded')),
  retention_until_ms BIGINT NULL,
  created_at_ms BIGINT NOT NULL,
  updated_at_ms BIGINT NOT NULL,
  UNIQUE(partner_user_id, version)
);

CREATE UNIQUE INDEX IF NOT EXISTS idx_partner_payout_profiles_current
  ON partner_payout_profiles(partner_user_id) WHERE status='current';
CREATE INDEX IF NOT EXISTS idx_partner_payout_profiles_retention
  ON partner_payout_profiles(retention_until_ms) WHERE retention_until_ms IS NOT NULL;

CREATE OR REPLACE FUNCTION protect_partner_payout_profile_history()
RETURNS trigger AS $$
BEGIN
  IF NEW.partner_user_id LIKE 'deleted:%' AND OLD.partner_user_id NOT LIKE 'deleted:%'
     AND (to_jsonb(NEW) - 'partner_user_id') = (to_jsonb(OLD) - 'partner_user_id') THEN
    RETURN NEW;
  END IF;
  IF OLD.status='current' AND NEW.status='superseded'
     AND (to_jsonb(NEW) - 'status' - 'updated_at_ms') = (to_jsonb(OLD) - 'status' - 'updated_at_ms') THEN
    RETURN NEW;
  END IF;
  RAISE EXCEPTION 'partner payout profile versions are immutable';
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trg_partner_payout_profile_immutable ON partner_payout_profiles;
CREATE TRIGGER trg_partner_payout_profile_immutable
BEFORE UPDATE OR DELETE ON partner_payout_profiles
FOR EACH ROW EXECUTE FUNCTION protect_partner_payout_profile_history();

ALTER TABLE partner_payout_requests
  ADD COLUMN IF NOT EXISTS payout_profile_id TEXT NULL REFERENCES partner_payout_profiles(payout_profile_id);

CREATE INDEX IF NOT EXISTS idx_partner_payout_partner_status_time
  ON partner_payout_requests(partner_user_id, status, requested_at_ms DESC);
CREATE INDEX IF NOT EXISTS idx_partner_ledger_source_lookup
  ON partner_commission_ledger(source_type, source_id, entry_type);

CREATE OR REPLACE FUNCTION detach_partner_links_on_account_delete()
RETURNS trigger AS $$
DECLARE anonymized_id TEXT;
BEGIN
  anonymized_id := 'deleted:' || COALESCE(
    (SELECT profile_id FROM partner_profiles WHERE user_id=OLD.user_id), md5(OLD.user_id)
  );
  UPDATE promotion_links SET status='inactive', updated_at_ms=(EXTRACT(EPOCH FROM clock_timestamp()) * 1000)::BIGINT
   WHERE owner_user_id=OLD.user_id AND link_kind='partner';
  UPDATE partner_commission_ledger SET partner_user_id=anonymized_id WHERE partner_user_id=OLD.user_id;
  UPDATE partner_payout_requests SET partner_user_id=anonymized_id WHERE partner_user_id=OLD.user_id;
  UPDATE partner_payout_profiles SET partner_user_id=anonymized_id WHERE partner_user_id=OLD.user_id;
  RETURN OLD;
END;
$$ LANGUAGE plpgsql;
