-- Bill web-grounded detailed answers as a distinct, idempotent usage kind.

ALTER TABLE billing_usage_reservations
  DROP CONSTRAINT IF EXISTS billing_usage_reservations_usage_kind_check;
ALTER TABLE billing_usage_reservations
  ADD CONSTRAINT billing_usage_reservations_usage_kind_check
  CHECK (usage_kind IN ('answer', 'web_answer', 'screenshot_answer', 'realtime_minute', 'written_exam_entry'));
