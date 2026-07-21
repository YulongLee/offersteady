## ADDED Requirements

### Requirement: Production redemption state survives runtime replacement

Configured production redemption codes, their ownership, idempotency records, and credit ledger entries SHALL remain authoritative after backend process restart, container replacement, or horizontal worker changes. A code successfully redeemed before runtime replacement MUST NOT become available again.

#### Scenario: Backend restarts after a successful redemption
- **WHEN** a user successfully redeems a configured code and the backend container is replaced
- **THEN** the same account receives its prior redemption result and another account receives only the generic unavailable outcome

### Requirement: Production code inventory uses non-reversible lookup records

The production database MUST store a keyed digest and masked hint instead of plaintext configured redemption codes. The digest key MUST be server-only and independently configurable from public client configuration.

#### Scenario: Operator inspects redemption tables
- **WHEN** an authorized operator inspects persisted code inventory and redemption records
- **THEN** the operator can audit status, points, owner, timestamps, and masked hint without finding a redeemable plaintext code

### Requirement: Concurrent production redemption is atomic

Production redemption SHALL lock or otherwise serialize the code lifecycle transition and credit insertion in one database transaction. Exactly one credit entry MUST be committed for a globally single-use code.

#### Scenario: Two accounts redeem the same code concurrently
- **WHEN** two valid requests for the same active code race across separate backend workers
- **THEN** one request credits the code and the other returns the generic unavailable outcome without a second ledger credit
