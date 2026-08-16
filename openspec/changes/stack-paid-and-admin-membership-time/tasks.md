## 1. Membership stacking implementation

- [x] 1.1 Make paid time-pass confirmation use the latest end across paid and admin entitlements.
- [x] 1.2 Serialize admin time grants with paid grants using the shared per-user advisory lock.
- [x] 1.3 Show cumulative remaining time and final expiry for continuous queued extensions.
- [x] 1.4 Remove the redundant standalone queued-membership details panel.

## 2. Regression verification

- [x] 2.1 Add a PostgreSQL regression test covering an active admin entitlement followed by a paid pass and duplicate payment confirmation.
- [x] 2.2 Run targeted backend tests and strict OpenSpec validation.
- [x] 2.3 Run the complete backend test suite and relevant repository checks.
- [x] 2.4 Run membership UI regression tests, Web typecheck, build, and strict OpenSpec validation.

## 3. Delivery and repair

- [x] 3.1 Commit and push only the scoped membership-stacking changes.
- [x] 3.2 Deploy the verified revision and confirm production health.
- [x] 3.3 Repair the verified overlapping paid entitlement in a guarded transaction and confirm the cumulative final expiry.
- [ ] 3.4 Commit, push, deploy, and verify the simplified membership page.
