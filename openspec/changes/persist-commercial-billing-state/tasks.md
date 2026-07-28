## 1. Contract

- [x] 1.1 Define durable wallet, order, entitlement and reservation behavior.

## 2. Database and repository

- [x] 2.1 Add billing persistence schema and immutable unified ledger migration.
- [x] 2.2 Implement PostgreSQL billing repository with transactional idempotency.

## 3. Service integration

- [x] 3.1 Route billing state, orders, payment callbacks and indexing accounting through the repository.
- [x] 3.2 Require persistent billing in production while preserving development/test memory behavior.

## 4. Verification and release

- [x] 4.1 Add restart, duplicate callback and concurrent reservation regression tests.
- [x] 4.2 Run backend regression tests and strict OpenSpec validation.
- [x] 4.3 Deploy migration and backend, then verify online health and persisted billing behavior.

## 5. Compact Points History

- [x] 5.1 Group negative ledger entries by business consumption category in the Web presentation layer.
- [x] 5.2 Preserve immutable backend ledger rows and positive credit history.
- [x] 5.3 Run regression tests, deploy the Web application, and verify the production billing page.
