ALTER TABLE auth_sms_challenges
  ADD COLUMN IF NOT EXISTS code_digest TEXT NULL;
