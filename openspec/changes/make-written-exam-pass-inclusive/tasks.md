## 1. Backend billing behavior

- [x] 1.1 Change written-exam entry reservation to use the existing membership-first billing path instead of forcing wallet-only billing.
- [x] 1.2 Preserve the session-stable usage ID, 30-point wallet rate, idempotent settlement, insufficient-balance handling and reservation release behavior.

## 2. Regression coverage

- [x] 2.1 Add backend tests for one-day and longer active passes entering without a wallet deduction.
- [x] 2.2 Add backend tests for points users paying 30 points and repeated start requests not double charging.
- [x] 2.3 Update frontend tests for written-exam and billing-page disclosures.

## 3. User-facing descriptions

- [x] 3.1 Update the written-exam preparation and creation copy to distinguish member-free entry from the 30-point points-user rate.
- [x] 3.2 Update the billing catalog, consumption explanation and purchase confirmation copy without changing product rates or unrelated entitlements.

## 4. Verification and release

- [x] 4.1 Run OpenSpec strict validation, targeted backend/frontend tests, typecheck and production build.
- [x] 4.2 Confirm the deployment candidate changes only the intended billing and Web files; do not update the desktop companion or database schema.
- [x] 4.3 When the China production environment has no active interview, deploy the backend/Web change, run health and billing smoke checks, and retain a rollback image.
