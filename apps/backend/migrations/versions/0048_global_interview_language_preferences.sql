-- Global multilingual interview preference. Existing accounts retain English.
ALTER TABLE auth_users ADD COLUMN IF NOT EXISTS default_interview_language TEXT NOT NULL DEFAULT 'en-US';
ALTER TABLE auth_users DROP CONSTRAINT IF EXISTS auth_users_default_interview_language_check;
ALTER TABLE auth_users ADD CONSTRAINT auth_users_default_interview_language_check CHECK (default_interview_language IN ('zh-CN','en-US','ja-JP','ko-KR','vi-VN','th-TH','id-ID','ms-MY','fil-PH','hi-IN','ar-SA','fr-FR','de-DE','es-ES','pt-BR','ru-RU','it-IT','nl-NL','sv-SE','da-DK','fi-FI','nb-NO','el-GR','pl-PL','cs-CZ','hu-HU','ro-RO','bg-BG','hr-HR','sk-SK'));
