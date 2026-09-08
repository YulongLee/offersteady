-- Publish the approved Global catalogue v2 without changing historical orders or entitlements.
-- Provider mappings retain their product IDs but return to draft so Creem must be
-- revalidated against the new authoritative amount before checkout can be enabled.

DO $$
BEGIN
  IF NOT EXISTS (
    SELECT 1
    FROM global_commerce_plan_versions
    WHERE offer_code = 'global-interview-pass' AND plan_version = 2
  ) THEN
    INSERT INTO global_commerce_plan_versions (
      offer_code, plan_version, display_name, description, currency, price_cents,
      billing_mode, duration_days, copilot_minutes, screen_assist_uses,
      resume_jd_enabled, knowledge_base_enabled, written_exam_enabled,
      full_product_enabled, status, featured, display_order, created_at_ms
    ) VALUES
      ('global-interview-pass', 2, 'Interview Day Pass', 'Focused access for your interview day.', 'USD', 999,
       'one_time', 1, 180, NULL, TRUE, FALSE, TRUE, FALSE, 'draft', FALSE, 1, 1788624000000),
      ('global-pro-weekly', 2, 'Pro Weekly', 'Unlimited full-product access for interview week.', 'USD', 4999,
       'one_time', 7, NULL, NULL, TRUE, TRUE, TRUE, TRUE, 'draft', TRUE, 2, 1788624000000),
      ('global-pro-monthly', 2, 'Pro Monthly', 'Unlimited full-product access with monthly renewal.', 'USD', 9999,
       'recurring', 30, NULL, NULL, TRUE, TRUE, TRUE, TRUE, 'draft', FALSE, 3, 1788624000000),
      ('global-job-hunt', 2, 'Job Hunt', 'Unlimited full-product access for a focused job search.', 'USD', 19999,
       'one_time', 90, NULL, NULL, TRUE, TRUE, TRUE, TRUE, 'draft', FALSE, 4, 1788624000000);

    UPDATE global_commerce_plan_versions
    SET status = 'retired'
    WHERE offer_code IN (
      'global-interview-pass', 'global-pro-weekly', 'global-pro-monthly', 'global-job-hunt'
    ) AND status = 'active';

    UPDATE global_commerce_plan_versions
    SET status = 'active'
    WHERE plan_version = 2
      AND offer_code IN (
        'global-interview-pass', 'global-pro-weekly', 'global-pro-monthly', 'global-job-hunt'
      );

    UPDATE global_commerce_product_mappings
    SET plan_version = 2,
        validation_status = 'draft',
        validated_amount_cents = NULL,
        validated_currency = NULL,
        validated_billing_mode = NULL,
        validated_at_ms = NULL,
        updated_at_ms = 1788624000000
    WHERE offer_code IN (
      'global-interview-pass', 'global-pro-weekly', 'global-pro-monthly', 'global-job-hunt'
    );

    UPDATE global_commerce_provider_configs
    SET enabled = FALSE,
        validation_status = 'draft',
        validation_errors = '["Global catalogue changed; validate all Creem product prices before enabling checkout."]'::jsonb,
        updated_at_ms = 1788624000000;
  END IF;
END $$;
