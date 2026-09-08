## ADDED Requirements

### Requirement: Global commerce administration is deployment-scoped
The Chinese-language operator console SHALL expose Global commerce controls only when connected to a Global-edition Backend. The Chinese production Backend SHALL not expose or execute Global commerce mutations.

#### Scenario: Operator opens Global administration
- **WHEN** an authorized operator uses the admin console on the Global deployment
- **THEN** Global plans, Creem readiness, orders, subscriptions, refunds, disputes, and diagnostics are available according to permission

#### Scenario: Operator opens Chinese administration
- **WHEN** the same admin build is connected to the Chinese edition
- **THEN** existing domestic payment/catalog views remain unchanged and Global commerce controls are unavailable

### Requirement: Plan changes are validated and versioned
Authorized operators SHALL be able to draft price, duration, quota, feature, publication, featured, and display-order changes. Publishing SHALL validate commercial invariants and create an immutable version rather than rewriting purchased benefits.

#### Scenario: Operator publishes a valid plan draft
- **WHEN** an authorized operator confirms a valid draft with reason and recent MFA
- **THEN** a new plan version becomes active and the prior version remains auditable

#### Scenario: Operator attempts an invalid offer
- **WHEN** a draft has an unsupported currency, nonpositive price, inconsistent Unlimited/quota fields, unsafe duration, or missing disclosure
- **THEN** publication is rejected with field-specific Chinese validation messages

### Requirement: Creem configuration is safe to operate
The admin SHALL show Test/Live mode, product mappings, webhook URL, masked credential readiness, provider validation, last accepted event, and activation state without returning API keys or webhook secrets.

#### Scenario: Operator reads configuration
- **WHEN** an authorized operator opens Creem settings
- **THEN** secret fields are represented only as configured/not configured plus nonreversible fingerprint metadata

#### Scenario: Mapping does not match provider product
- **WHEN** validation detects an amount, currency, billing-mode, environment, or status mismatch
- **THEN** activation remains disabled and the mismatch is shown without secret or customer data

### Requirement: Live activation requires deliberate approval
Enabling Live checkout SHALL require `payments.manage`, recent MFA, an explicit confirmation, a reason, and all readiness gates. Test and Live state MUST remain isolated.

#### Scenario: Finance operator enables Live mode
- **WHEN** all gates pass and an authorized operator confirms activation
- **THEN** new Global checkout creation becomes available and an immutable audit event records actor, time, configuration version, and reason

#### Scenario: Operator saves a sensitive change
- **WHEN** provider mapping, webhook, plan price, billing mode, or legal links change
- **THEN** Live checkout is automatically disabled pending revalidation

### Requirement: Operators can diagnose and reconcile commerce
Authorized operators SHALL be able to search redacted orders/subscriptions/events, inspect state transitions and webhook lag, trigger bounded reconciliation, and record refund/dispute handling without exposing payment credentials or interview content.

#### Scenario: Pending order is investigated
- **WHEN** an operator opens an order diagnostic
- **THEN** the console shows internal/provider references, masked customer identity, expected and confirmed financial facts, event history, reconciliation status, and safe actions

#### Scenario: Reconciliation is triggered
- **WHEN** an authorized operator confirms reconciliation for one order
- **THEN** the action is rate-limited, idempotent, audited, and uses the same provider-verification path as automatic processing

### Requirement: Commercial metrics include unit economics
The Global admin SHALL report provider-confirmed gross revenue, refunds, disputes, provider fees when available, estimated net revenue, measured service cost metadata, and estimated gross margin by plan/version without storing interview content.

#### Scenario: Unlimited plan cost rises
- **WHEN** estimated variable cost crosses the configured share of net revenue
- **THEN** the console raises a review alert without automatically interrupting active interviews

### Requirement: Sensitive operations are auditable
Plan publication, mapping changes, activation changes, reconciliation, refunds, subscription actions, and fair-use restrictions SHALL require least-privilege permissions and immutable audit records with no secret values.

#### Scenario: Unauthorized operator attempts a payment mutation
- **WHEN** an operator lacks the required permission or recent MFA
- **THEN** the action is rejected and the security event is recorded safely

### Requirement: Operators can find and support Global members
The Global operator console SHALL provide a dedicated member workspace that searches Global accounts by exact or partial email, display name, or user ID and shows the selected account's current and historical entitlements, remaining metered usage, included features, orders, and subscriptions. The Chinese deployment SHALL NOT expose this workspace.

#### Scenario: Operator searches by customer email
- **WHEN** an authorized operator enters all or part of a Global customer's email
- **THEN** matching accounts are returned with their current plan and expiry summary, and the operator can open one account without scanning an unbounded user table

#### Scenario: Operator opens member details
- **WHEN** an authorized operator selects a Global account
- **THEN** the console shows server-authoritative entitlement, usage, order, and subscription facts without returning password data, payment credentials, or interview content

### Requirement: Manual member adjustments preserve commercial history
An authorized operator MAY grant a current paid offer as a separately identified manual entitlement or revoke one selected entitlement. Manual grants MUST use the active plan's benefit snapshot and duration, MUST NOT create a paid order or provider subscription, and MUST NOT claim automatic renewal. Each adjustment SHALL require confirmation, a reason, recent MFA, idempotency, and an immutable audit record.

#### Scenario: Support grants a weekly membership
- **WHEN** an authorized operator confirms a Pro Weekly grant for a selected account
- **THEN** one seven-day admin-sourced entitlement with the current Pro Weekly benefits is created, no Creem order is fabricated, and a retry with the same idempotency key creates no duplicate

#### Scenario: Support revokes one entitlement
- **WHEN** an authorized operator confirms revocation of a selected active entitlement
- **THEN** only that entitlement is revoked, provider order and subscription history remain unchanged, and any other valid entitlement continues to apply
