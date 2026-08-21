DO $$
DECLARE
  constraint_definition TEXT;
BEGIN
  SELECT pg_get_constraintdef(oid)
    INTO constraint_definition
  FROM pg_constraint
  WHERE conrelid = 'admin_metric_snapshots'::regclass
    AND conname = 'admin_metric_snapshots_granularity_check';

  IF constraint_definition IS NULL
     OR constraint_definition NOT LIKE '%capacity_5m%' THEN
    ALTER TABLE admin_metric_snapshots
      DROP CONSTRAINT IF EXISTS admin_metric_snapshots_granularity_check;
    ALTER TABLE admin_metric_snapshots
      ADD CONSTRAINT admin_metric_snapshots_granularity_check
      CHECK (granularity IN ('capacity_5m', 'hourly', 'daily')) NOT VALID;
    ALTER TABLE admin_metric_snapshots
      VALIDATE CONSTRAINT admin_metric_snapshots_granularity_check;
  END IF;
END
$$;
