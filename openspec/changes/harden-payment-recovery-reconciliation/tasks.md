## 1. Contract

- [x] 1.1 Define callback audit, expiry, recovery and reconciliation behavior.

## 2. Persistence and service

- [x] 2.1 Add payment callback audit and reconciliation schema.
- [x] 2.2 Persist order expiry and expose expired status in existing responses.
- [x] 2.3 Record callback outcomes and reconciliation issues without raw secrets.
- [x] 2.4 Preserve idempotent entitlement delivery for duplicate and late callbacks.

## 3. Operations

- [x] 3.1 Add a server-only reconciliation report command.
- [x] 3.2 Correct production payment callback documentation to HTTPS.

## 4. Verification and release

- [x] 4.1 Add expiry, invalid signature, duplicate callback and mismatch regression tests.
- [x] 4.2 Run real PostgreSQL tests, full regression and strict OpenSpec validation.
- [ ] 4.3 Back up production data, deploy migration and verify online payment state.
