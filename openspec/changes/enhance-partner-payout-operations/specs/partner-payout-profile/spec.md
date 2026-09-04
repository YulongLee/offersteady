## ADDED Requirements

### Requirement: Partner payout profiles collect only minimum settlement data
An active partner SHALL be able to save either an Alipay or WeChat payout method, a natural-person account name and an account identifier. The system MUST NOT request an identity-card number, bank-card number, payout QR image, interview content or unrelated personal data.

#### Scenario: Partner saves a valid payout profile
- **WHEN** an active partner confirms a supported method, valid account name and valid account identifier
- **THEN** the system creates a new active payout-profile version and returns only method and masked display values

#### Scenario: Non-partner attempts to save payout data
- **WHEN** an authenticated user who has not joined the partner program submits payout details
- **THEN** the request is rejected without persisting the submitted values

### Requirement: Payout data is encrypted and masked by default
The system SHALL encrypt account name and account identifier with a dedicated server-side production key before persistence. Plaintext MUST NOT appear in logs, audit details, analytics, list responses, client storage or test fixtures; user and administrator list views SHALL receive masked values only.

#### Scenario: Administrator lists settlement requests
- **WHEN** any active administrator opens partner reconciliation
- **THEN** the response contains payout method and masked account status but no plaintext name or account identifier

#### Scenario: Encryption key is unavailable
- **WHEN** payout-profile storage is enabled but the dedicated encryption key is missing or invalid
- **THEN** payout-profile writes fail closed while interviews, ASR, answers, screenshots and payments continue normally

### Requirement: Payout profile updates preserve immutable history
Each accepted update SHALL create a new payout-profile version and deactivate the previous current version. A settlement request MUST reference the exact profile version selected at submission so later edits cannot change its payout destination.

#### Scenario: Partner changes account after requesting settlement
- **WHEN** a partner submits a settlement request and later replaces the payout account
- **THEN** the existing request remains bound to the earlier encrypted profile version and future requests use the new version

### Requirement: Plaintext payout access requires step-up and audit
Only an administrator with `promotion.payout.manage` and recent MFA SHALL be able to reveal the payout details for one specific settlement request. Each reveal attempt MUST be audited, the response MUST disable caching, and no batch plaintext export SHALL exist.

#### Scenario: Finance administrator reveals one payout target
- **WHEN** an authorized recently verified administrator requests the payout target for one pending or approved settlement
- **THEN** the system returns that request’s name and account identifier once with `Cache-Control: no-store` and appends an audit event

#### Scenario: Read-only administrator attempts reveal
- **WHEN** an administrator with aggregate partner read access but without payout-management permission requests plaintext payout data
- **THEN** the request is rejected, no plaintext is returned and the failed attempt is audited

### Requirement: Saving payout details does not imply automatic transfer
Until an official payout provider is configured, the product SHALL describe settlement as manually reviewed and paid. A settlement MUST become paid only after an authorized administrator records a real external payment reference.

#### Scenario: Partner saves an Alipay account
- **WHEN** the payout profile is saved but no official transfer provider is configured
- **THEN** no transfer request is sent and the dashboard continues to show the manual settlement process
