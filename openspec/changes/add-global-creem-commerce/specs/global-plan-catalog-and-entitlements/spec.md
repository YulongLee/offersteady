## ADDED Requirements

### Requirement: Global catalogue publishes the approved offers
The Global service SHALL publish exactly the active server-owned versions of Free, Interview Day Pass, Pro Weekly, Pro Monthly, and Job Hunt with USD base price, billing mode, duration, benefits, display order, and featured state. Browser input MUST NOT determine an authoritative price or entitlement.

#### Scenario: Customer opens Global pricing
- **WHEN** an authenticated or public customer opens the Global pricing experience
- **THEN** the service returns the active offer versions and identifies Pro Weekly as the initial featured offer

#### Scenario: Operator edits a benefit
- **WHEN** an authorized operator publishes changed pricing or benefits
- **THEN** the system creates a new immutable plan version and existing entitlements retain their purchased benefit snapshot

### Requirement: Free allowance is granted once per Global account
The system SHALL grant each verified Global account exactly one no-card Free entitlement containing 15 Copilot minutes and 3 Screen Assist uses, with no calendar reset.

#### Scenario: New email account is verified
- **WHEN** a Global user completes first email verification
- **THEN** the system atomically creates one Free grant for that account

#### Scenario: Existing account first reads entitlements
- **WHEN** an existing Global account without a recorded Free grant requests entitlement state
- **THEN** the system lazily creates the same one-time grant idempotently

#### Scenario: Exhausted Free account returns later
- **WHEN** the account has consumed its 15 minutes and 3 Screen Assist uses
- **THEN** neither time passage, sign-out, browser changes, nor another entitlement read replenishes the grant

### Requirement: Paid plans grant approved benefits
The system SHALL grant Interview Day Pass for 24 hours with 180 Copilot minutes, unlimited Screen Assist, and Resume/JD access; Pro Weekly for 7 days with full Unlimited access; Pro Monthly for each provider-confirmed monthly period with full Unlimited access; and Job Hunt for 90 days with full Unlimited access.

#### Scenario: Interview Day Pass is fulfilled
- **WHEN** a verified one-time Interview Day Pass payment is fulfilled
- **THEN** the entitlement contains the approved duration, 180-minute quota, unlimited Screen Assist, and Resume/JD feature flags

#### Scenario: Pro offer is fulfilled
- **WHEN** a verified Pro Weekly, Pro Monthly, or Job Hunt payment period is fulfilled
- **THEN** the entitlement contains full current Global feature access and no ordinary Copilot-minute or Screen-Assist balance

### Requirement: Usage accounting is atomic and idempotent
Global quota usage SHALL use durable reservation, settlement, and release operations bound to a stable operation ID. Internal failures MUST release unused reservations, and retries MUST NOT consume the same allowance twice.

#### Scenario: Metered Copilot session ends
- **WHEN** a Free or Interview Day Pass Copilot session finishes
- **THEN** the system settles actual billable elapsed minutes once and exposes the remaining balance

#### Scenario: Screen Assist fails internally
- **WHEN** a metered Screen Assist operation is reserved but the service fails before delivering an answer
- **THEN** the reserved use is released and remains available

### Requirement: Fair use is transparent and session-safe
Unlimited offers SHALL have no ordinary hidden minute, Screen Assist, or interview-length cap. Fair-use controls SHALL be publicly disclosed, SHALL use usage metadata rather than interview content, and MUST NOT terminate or degrade an interview already in progress based on an automated decision.

#### Scenario: Long legitimate interview continues
- **WHEN** an Unlimited customer remains in one legitimate interview for an unusually long duration
- **THEN** the active interview continues without a hidden balance cutoff

#### Scenario: Automated abuse is detected
- **WHEN** durable evidence indicates account sharing, excessive concurrency, automation, resale, or abusive traffic
- **THEN** the system records a reviewable restriction for future session creation with reason, expiry/review state, and support path

### Requirement: Global and domestic entitlements remain isolated
Global entitlement and usage decisions SHALL require the Global product edition and SHALL NOT read or mutate domestic points, time-pass, payment, or referral state.

#### Scenario: Chinese edition processes usage
- **WHEN** the Chinese product authorizes or settles a billable operation
- **THEN** the existing domestic billing path executes without reading or writing Global commerce tables
