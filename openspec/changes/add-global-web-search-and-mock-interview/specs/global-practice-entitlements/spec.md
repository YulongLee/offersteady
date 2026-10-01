## ADDED Requirements

### Requirement: Seven-day paid membership gate
Global web-grounded answers and mock creation/start MUST require an active, non-revoked Global entitlement whose purchased immutable plan version has duration_days >= 7. Free, one-day, future, expired and revoked entitlements MUST NOT qualify. No CN billing table SHALL be read or written.

#### Scenario: Weekly member nearing expiry
- **WHEN** a weekly membership has only one hour remaining
- **THEN** new feature access remains available until its expiry; remaining days are not the eligibility test

#### Scenario: Server enforcement
- **WHEN** an ineligible client bypasses the UI or claims a free billing class
- **THEN** the server rejects it before provider use or quota mutation

### Requirement: Atomic daily quota and record slots
Global mock interviews SHALL allow at most three creations per UTC day and two retained or in-progress records per owner. Retries MUST be idempotent. Deletion or cancellation MUST NOT restore the daily creation quota. No entry, minute or web-answer points SHALL be charged.

#### Scenario: Fourth creation
- **WHEN** three non-refunded creations exist today, even if deleted
- **THEN** another creation is refused until the next UTC day

#### Scenario: Concurrent requests
- **WHEN** simultaneous requests compete for the last quota or record slot
- **THEN** only the allowed number succeed and duplicate idempotency keys return the same record

#### Scenario: Model cannot complete any question
- **WHEN** the trusted terminal provider-fault path ends a session before a submitted answer
- **THEN** its daily quota is restored at most once; user cancellation does not use this path

### Requirement: Existing sessions and commerce remain unaffected
Membership expiry SHALL block new starts but SHALL NOT interrupt an already started mock interview or owner access to saved reports. Current prices, historical plan snapshots and ordinary Copilot allowances MUST remain unchanged.

#### Scenario: Expiry during practice
- **WHEN** a membership expires after practice starts
- **THEN** that practice and report remain available without adding minute charges
