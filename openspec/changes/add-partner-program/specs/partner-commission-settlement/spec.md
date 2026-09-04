## ADDED Requirements

### Requirement: Commission uses versioned net-receipt rules
The system SHALL calculate commission from authoritative paid order value less authoritative refunds or chargebacks, using a snapshotted rate of 2000 basis points for the initial version. Monetary values MUST use integer cents and each order/rule version MUST be projected idempotently.

#### Scenario: Eligible order becomes paid
- **WHEN** an eligible attributed order reaches authoritative paid state for CNY 100.00
- **THEN** the ledger records one pending CNY 20.00 commission entry with the rate and rule version snapshot

#### Scenario: Projection is replayed
- **WHEN** the projection job reads the same order and rule version again
- **THEN** no duplicate commission amount or ledger entry is created

### Requirement: Refunds and chargebacks are append-only reversals
The system SHALL append an auditable reversal when an eligible order is refunded or charged back. It MUST NOT overwrite or delete the original earning entry, and a repeated refund observation MUST be idempotent.

#### Scenario: Paid order is fully refunded
- **WHEN** a CNY 100.00 eligible paid order with CNY 20.00 pending commission is fully refunded
- **THEN** the ledger appends a CNY -20.00 reversal and the order contributes zero net commission

### Requirement: Commission observes a refund hold
An earning SHALL remain pending until seven complete days after authoritative payment and SHALL become available only if it has not been reversed. The hold duration MUST be configuration-backed and snapshotted for audit.

#### Scenario: Observation period completes
- **WHEN** an unreversed earning reaches its recorded eligible time
- **THEN** it becomes available for settlement without changing its original amount or rule snapshot

### Requirement: Settlement requests obey monthly limits
An active partner SHALL be able to request settlement only when available commission is at least CNY 100.00 and SHALL create at most one request per `Asia/Shanghai` calendar month. Requested funds MUST be reserved atomically so concurrent requests cannot spend the same balance twice.

#### Scenario: Eligible partner requests monthly settlement
- **WHEN** a partner has CNY 150.00 available and no request in the current month
- **THEN** the system creates one CNY 150.00 requested settlement and removes that amount from freely available balance

#### Scenario: Partner submits two concurrent requests
- **WHEN** two current-month requests arrive concurrently for the same partner
- **THEN** exactly one request succeeds and the commission balance is reserved once

### Requirement: Administrators audit settlement decisions
Only an administrator with the required promotion finance permission SHALL approve, reject or mark a settlement paid. Each transition MUST record the actor, timestamp, reason, previous state and a non-sensitive payment reference; invalid state transitions MUST be rejected.

All active administrators SHALL be able to discover and read the aggregate partner reconciliation view when promotion analytics is enabled. Read access MUST NOT grant permission to project commissions, record refund reversals, approve or reject requests, or mark a request paid.

#### Scenario: Existing administrator opens partner reconciliation
- **WHEN** an active administrator whose existing session predates the partner feature opens the admin platform while promotion analytics is enabled
- **THEN** the promotion center and partner reconciliation tab are visible with aggregate read-only data without requiring a new login

#### Scenario: Read-only administrator sees settlement actions
- **WHEN** an administrator has partner reconciliation read access but lacks the promotion finance permission
- **THEN** partner and payout aggregates remain visible while projection, refund and payout-transition actions are hidden and rejected by the API

#### Scenario: Administrator marks an approved request paid
- **WHEN** an authorized administrator records a payment reference for an approved request
- **THEN** the request becomes paid, the reserved commission becomes settled, and the audit record retains the transition

#### Scenario: Unauthorized administrator attempts approval
- **WHEN** an administrator without the settlement permission attempts a transition
- **THEN** the request remains unchanged and the operation is rejected
