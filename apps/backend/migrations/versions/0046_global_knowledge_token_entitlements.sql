ALTER TABLE global_commerce_plan_versions
  ADD COLUMN IF NOT EXISTS knowledge_tokens INTEGER NOT NULL DEFAULT 0;
ALTER TABLE global_commerce_entitlements
  ADD COLUMN IF NOT EXISTS knowledge_tokens_granted INTEGER NOT NULL DEFAULT 0,
  ADD COLUMN IF NOT EXISTS knowledge_tokens_used INTEGER NOT NULL DEFAULT 0,
  ADD COLUMN IF NOT EXISTS knowledge_tokens_locked INTEGER NOT NULL DEFAULT 0;
ALTER TABLE global_commerce_usage_reservations
  DROP CONSTRAINT IF EXISTS global_commerce_usage_reservations_usage_kind_check;
ALTER TABLE global_commerce_usage_reservations
  ADD CONSTRAINT global_commerce_usage_reservations_usage_kind_check
  CHECK (usage_kind IN ('copilot_minute', 'screen_assist', 'knowledge_token'));

UPDATE global_commerce_plan_versions
SET knowledge_tokens = CASE offer_code
  WHEN 'global-free' THEN 0
  WHEN 'global-interview-pass' THEN 0
  WHEN 'global-pro-weekly' THEN 50000
  WHEN 'global-pro-monthly' THEN 200000
  WHEN 'global-job-hunt' THEN 1000000
  ELSE knowledge_tokens
END
WHERE status = 'active';

UPDATE global_commerce_entitlements e
SET knowledge_tokens_granted = p.knowledge_tokens
FROM global_commerce_plan_versions p
WHERE e.offer_code = p.offer_code
  AND e.plan_version = p.plan_version
  AND e.knowledge_tokens_granted = 0
  AND p.knowledge_tokens > 0;
