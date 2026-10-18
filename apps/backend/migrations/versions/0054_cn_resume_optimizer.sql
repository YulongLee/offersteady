CREATE TABLE IF NOT EXISTS cn_resume_optimizer_jobs (
    job_id TEXT PRIMARY KEY,
    owner_user_id TEXT NOT NULL,
    idempotency_key TEXT NOT NULL,
    input_fingerprint TEXT NOT NULL,
    source_document_id TEXT NOT NULL,
    source_version_id TEXT NOT NULL,
    jd_document_id TEXT NULL,
    jd_version_id TEXT NULL,
    status TEXT NOT NULL CHECK (status IN ('queued','running','completed','failed','cancelled')),
    revision INTEGER NOT NULL DEFAULT 1,
    quota_day DATE NOT NULL,
    created_at_ms BIGINT NOT NULL,
    updated_at_ms BIGINT NOT NULL,
    completed_at_ms BIGINT NULL,
    deleted_at_ms BIGINT NULL,
    lease_until_ms BIGINT NULL,
    claim_token TEXT NULL,
    error_code TEXT NULL,
    payload JSONB NOT NULL DEFAULT '{}'::jsonb,
    UNIQUE (owner_user_id, idempotency_key)
);
CREATE INDEX IF NOT EXISTS cn_resume_optimizer_owner_history_idx
    ON cn_resume_optimizer_jobs(owner_user_id, created_at_ms DESC) WHERE deleted_at_ms IS NULL;
CREATE INDEX IF NOT EXISTS cn_resume_optimizer_active_idx
    ON cn_resume_optimizer_jobs(status, created_at_ms) WHERE status IN ('queued','running') AND deleted_at_ms IS NULL;
CREATE INDEX IF NOT EXISTS cn_resume_optimizer_source_idx ON cn_resume_optimizer_jobs(source_document_id);
CREATE INDEX IF NOT EXISTS cn_resume_optimizer_jd_idx ON cn_resume_optimizer_jobs(jd_document_id) WHERE jd_document_id IS NOT NULL;
CREATE TABLE IF NOT EXISTS cn_resume_optimizer_usage (
    job_id TEXT PRIMARY KEY REFERENCES cn_resume_optimizer_jobs(job_id),
    owner_user_id TEXT NOT NULL,
    quota_day DATE NOT NULL,
    membership_entitlement_id TEXT NULL,
    billing_class TEXT NOT NULL CHECK(billing_class IN ('daily_pass_free','points')),
    points_charged INTEGER NOT NULL CHECK(points_charged IN (0,100)),
    CHECK ((billing_class='daily_pass_free' AND points_charged=0 AND membership_entitlement_id IS NOT NULL) OR (billing_class='points' AND points_charged=100)),
    status TEXT NOT NULL CHECK (status IN ('reserved','settled','released')),
    created_at_ms BIGINT NOT NULL,
    finalized_at_ms BIGINT NULL
);
CREATE INDEX IF NOT EXISTS cn_resume_optimizer_usage_day_idx
    ON cn_resume_optimizer_usage(owner_user_id, quota_day, status);

-- Expand the actual old expressions, including unrecognised legitimate kinds.
-- No immutable row or old trigger is modified. Missing guards fail closed.
DO $$
DECLARE kind_expression TEXT; points_expression TEXT;
BEGIN
  SELECT pg_get_expr(conbin,conrelid) INTO kind_expression FROM pg_constraint
    WHERE conrelid='points_redemption_ledger'::regclass
      AND conname='points_redemption_ledger_kind_check' AND contype='c';
  SELECT pg_get_expr(conbin,conrelid) INTO points_expression FROM pg_constraint
    WHERE conrelid='points_redemption_ledger'::regclass
      AND conname='points_redemption_ledger_points_check' AND contype='c';
  IF kind_expression IS NULL OR points_expression IS NULL THEN
    RAISE EXCEPTION 'cn_resume_optimizer_missing_wallet_guards';
  END IF;
  ALTER TABLE points_redemption_ledger DROP CONSTRAINT points_redemption_ledger_kind_check;
  EXECUTE format('ALTER TABLE points_redemption_ledger ADD CONSTRAINT points_redemption_ledger_kind_check CHECK ((%s) OR (kind=''resume_optimizer_charge'' AND points=-100) OR (kind=''resume_optimizer_refund'' AND points=100))',kind_expression);
  ALTER TABLE points_redemption_ledger DROP CONSTRAINT points_redemption_ledger_points_check;
  EXECUTE format('ALTER TABLE points_redemption_ledger ADD CONSTRAINT points_redemption_ledger_points_check CHECK ((%s) OR (kind=''resume_optimizer_charge'' AND points=-100) OR (kind=''resume_optimizer_refund'' AND points=100))',points_expression);
END $$;
