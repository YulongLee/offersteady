-- Runtime operator switch for partner recruitment. Historical finance data is untouched.

CREATE TABLE IF NOT EXISTS partner_program_settings (
  settings_id TEXT PRIMARY KEY,
  enabled BOOLEAN NOT NULL,
  config_version INTEGER NOT NULL CHECK (config_version > 0),
  updated_by_user_id TEXT NULL,
  updated_at_ms BIGINT NOT NULL
);

INSERT INTO partner_program_settings (
  settings_id, enabled, config_version, updated_by_user_id, updated_at_ms
) VALUES ('default', TRUE, 1, NULL, 0)
ON CONFLICT (settings_id) DO NOTHING;
