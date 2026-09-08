-- Accept the full current Creem subscription lifecycle without changing any
-- existing order, entitlement, or non-commerce schema.
ALTER TABLE global_commerce_subscriptions
  DROP CONSTRAINT IF EXISTS global_commerce_subscriptions_status_check;

ALTER TABLE global_commerce_subscriptions
  ADD CONSTRAINT global_commerce_subscriptions_status_check
  CHECK (status IN (
    'trialing','active','past_due','unpaid','canceling','canceled','paused','expired'
  ));
