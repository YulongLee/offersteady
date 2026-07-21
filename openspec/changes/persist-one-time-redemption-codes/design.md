## Context

`BillingService` currently owns redemption inventory, usage state, and ledger records in Python dictionaries. Configured test-distribution codes therefore lose their used state whenever the backend process is recreated. The existing product specification already expects server-authoritative, one-time, idempotent redemption with an immutable wallet record.

## Goals

- Make configured production codes globally one-time across users, workers, and restarts.
- Preserve same-request idempotency and same-owner recovery.
- Avoid storing plaintext bearer codes in PostgreSQL, logs, API responses, or Git.
- Keep the current frontend and API response shape.

## Non-Goals

- Migrating payment orders, time passes, or every existing prototype ledger mutation in this change.
- Adding an administrator campaign-management UI.
- Reconstructing redemptions that happened before durable storage existed.

## Decisions

### PostgreSQL is authoritative for configured codes

At backend startup, configured code values are normalized and synchronized into `points_redemption_codes` as HMAC-SHA256 digests. The HMAC key is supplied independently through `OFFERSTEADY_REDEMPTION_CODE_PEPPER`. Database rows retain only the digest, a masked last-four hint, points, and lifecycle metadata.

### Redemption is one database transaction

The repository takes a transaction-scoped advisory lock for the account/idempotency pair, then locks the matching code row with `SELECT ... FOR UPDATE`. It writes one immutable `redemption_credit` ledger row, one redemption row, and the code ownership transition before commit. A uniqueness constraint on the code digest and account/idempotency pair provides a second safety boundary.

### Billing merges durable and prototype ledgers

Configured-code credits are read from PostgreSQL and merged with the existing in-memory prototype ledger for state and balance calculations. This keeps the scope narrow while ensuring distributed test-code points survive backend restarts and can fund knowledge-index operations.

### Production fails closed

When configured redemption codes are enabled in production, both PostgreSQL and a non-empty digest pepper are required. Development and test environments can retain the current in-memory implementation when durable dependencies are absent.

## Rollback

Deploying the previous application version leaves the additive tables untouched. The migration is not destructively rolled back because deleting redemption evidence could permit code reuse. If necessary, disable redemption at the API/configuration layer while retaining the tables for audit and a later forward fix.

## Verification

- Run backend tests, including service behavior and an optional PostgreSQL integration test.
- Run `openspec validate persist-one-time-redemption-codes --strict`.
- In production, confirm 100 configured code digests exist, no plaintext code is stored, and a redeemed code remains unavailable after a backend restart.
