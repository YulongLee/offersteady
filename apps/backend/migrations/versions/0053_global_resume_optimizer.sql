CREATE TABLE IF NOT EXISTS global_resume_optimizer_jobs (
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
CREATE INDEX IF NOT EXISTS global_resume_optimizer_owner_history_idx
    ON global_resume_optimizer_jobs(owner_user_id, created_at_ms DESC) WHERE deleted_at_ms IS NULL;
CREATE INDEX IF NOT EXISTS global_resume_optimizer_active_idx
    ON global_resume_optimizer_jobs(status, created_at_ms) WHERE status IN ('queued','running') AND deleted_at_ms IS NULL;
CREATE INDEX IF NOT EXISTS global_resume_optimizer_source_idx ON global_resume_optimizer_jobs(source_document_id);
CREATE INDEX IF NOT EXISTS global_resume_optimizer_jd_idx ON global_resume_optimizer_jobs(jd_document_id) WHERE jd_document_id IS NOT NULL;
CREATE TABLE IF NOT EXISTS global_resume_optimizer_usage (
    job_id TEXT PRIMARY KEY REFERENCES global_resume_optimizer_jobs(job_id),
    owner_user_id TEXT NOT NULL,
    quota_day DATE NOT NULL,
    membership_entitlement_id TEXT NOT NULL,
    status TEXT NOT NULL CHECK (status IN ('reserved','settled','released')),
    created_at_ms BIGINT NOT NULL,
    finalized_at_ms BIGINT NULL
);
CREATE INDEX IF NOT EXISTS global_resume_optimizer_usage_day_idx
    ON global_resume_optimizer_usage(owner_user_id, quota_day, status);
