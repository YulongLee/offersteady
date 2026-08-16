## 1. Membership stacking implementation

- [x] 1.1 Make paid time-pass confirmation use the latest end across paid and admin entitlements.
- [x] 1.2 Serialize admin time grants with paid grants using the shared per-user advisory lock.

## 2. Regression verification

- [x] 2.1 Add a PostgreSQL regression test covering an active admin entitlement followed by a paid pass and duplicate payment confirmation.
- [x] 2.2 Run targeted backend tests and strict OpenSpec validation.
- [x] 2.3 Run the complete backend test suite and relevant repository checks.

## 3. Delivery and repair

- [ ] 3.1 Commit and push only the scoped membership-stacking changes.
- [ ] 3.2 Deploy the verified revision and confirm production health.
- [ ] 3.3 Repair the verified overlapping paid entitlement in a guarded transaction and confirm the cumulative final expiry.
