## 1. Specification and storage

- [x] 1.1 Define durable one-time, privacy, idempotency, and restart requirements.
- [x] 1.2 Add the additive PostgreSQL redemption inventory, redemption, and immutable ledger migration.

## 2. Backend implementation

- [x] 2.1 Add the points-redemption persistence port and PostgreSQL repository.
- [x] 2.2 Wire production dependency selection and fail-closed secret requirements.
- [x] 2.3 Merge persistent redemption credits into billing state and spendable balance.

## 3. Verification and release

- [x] 3.1 Add regression coverage for one-time, replay, privacy, restart, and concurrency behavior.
- [x] 3.2 Run backend tests and strict OpenSpec validation.
- [x] 3.3 Commit, push, deploy, and verify configured inventory on the production server.
