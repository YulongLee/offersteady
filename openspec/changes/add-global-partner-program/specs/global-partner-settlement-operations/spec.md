## ADDED Requirements

### Requirement: Global payout profiles collect only minimum configurable identifiers
An active Global partner SHALL be able to save a supported payout method, recipient name and provider account identifier. Supported methods SHALL be deployment-configurable; the initial implementation MUST NOT collect card numbers, bank credentials, identity documents, QR images or interview data.

#### Scenario: Partner saves a supported payout profile
- **WHEN** an active partner confirms valid details for an enabled method such as PayPal or Wise
- **THEN** the system creates an encrypted version and returns only the method and masked display values

#### Scenario: Unsupported payout method is submitted
- **WHEN** a client submits a method not enabled by Global operations
- **THEN** the request is rejected without persisting the submitted identifier

### Requirement: Payout information is encrypted, versioned and masked
Payout identifiers SHALL use a dedicated Global server-side encryption key. Updates MUST create immutable versions, and each settlement request MUST reference its selected version. Plaintext MUST NOT enter logs, analytics, exports or default API responses.

#### Scenario: Partner changes payout destination
- **WHEN** a partner changes payout details after submitting a settlement request
- **THEN** the existing request keeps the prior encrypted version and future requests use the new version

### Requirement: Settlement remains manual and auditable
The first Global release SHALL use monthly manual settlement. An authorized operator SHALL approve, reject or mark an approved request paid with a non-sensitive external reference; marking paid SHALL append ledger settlement entries and prevent duplicate payment.

#### Scenario: Operator records completed payment
- **WHEN** an authorized operator confirms an approved request was paid and records a reference
- **THEN** the request becomes settled once, balances update from the append-only ledger and an audit event is retained

#### Scenario: Partner has not requested settlement
- **WHEN** no settlement request exists
- **THEN** an operator cannot arbitrarily zero or mark the partner's available balance paid

### Requirement: Global administrators can reconcile each partner and order
The Chinese Global-admin console SHALL show per-partner pending, available, reserved, reversed and settled USD commission; order-level earnings and reversals; payout requests; masked destinations; and aggregate totals. Queries MUST be bounded and isolated from interview hot paths.

#### Scenario: Finance reviews one partner
- **WHEN** an authorized operator opens a partner record
- **THEN** the console shows that partner's commission-state breakdown and matching order/settlement references without referred-user PII

### Requirement: Sensitive payout access requires least privilege and audit
Only an operator with the dedicated payout permission and recent MFA SHALL reveal one settlement request's full payout identifier. Each reveal attempt MUST be audited and returned with no-store caching headers; bulk plaintext export MUST NOT exist.

#### Scenario: Authorized operator prepares one manual payout
- **WHEN** a recently verified payout operator reveals one pending or approved request
- **THEN** only that request's payout details are returned temporarily and the access is audited

### Requirement: Global partner operations remain isolated from domestic production
Global partner schemas, configuration, links, commissions and payout data SHALL use the Global database and Global product-edition gate. A Global release MUST NOT modify or deploy Chinese Web, Chinese Admin, domestic partner data or domestic payment behavior.

#### Scenario: Global partner release is deployed
- **WHEN** the Global-only release is built and rolled out
- **THEN** domestic source/build checks remain unchanged and the Chinese production health checks continue to pass
