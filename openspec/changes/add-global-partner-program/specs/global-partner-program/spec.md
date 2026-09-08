## ADDED Requirements

### Requirement: Global visitors can discover the partner program without workbench disruption
The Global public homepage SHALL show a concise English Partner Program section near the bottom while the Global activity is enabled. The authenticated workbench and live interview navigation MUST NOT contain the activity entry.

#### Scenario: Visitor opens the enabled Global homepage
- **WHEN** a visitor opens `offersteady.com` while Global partner recruitment is enabled
- **THEN** the page shows a Partner Program CTA describing a 20% referral commission and links to the protected partner page

#### Scenario: Customer opens the interview workbench
- **WHEN** an authenticated customer opens a workbench or live interview route
- **THEN** partner promotion UI does not cover, delay or alter interview controls

### Requirement: Each verified Global partner receives one durable first-level link
An authenticated verified Global user SHALL be able to accept the current agreement and receive one durable Global referral link. Self-referral, recursive attribution and multi-level commissions MUST be rejected.

#### Scenario: Verified customer joins once
- **WHEN** an eligible customer accepts the current Partner Program agreement
- **THEN** the system idempotently creates one partner profile and one reusable `offersteady.com` referral link

#### Scenario: Partner attempts self-referral
- **WHEN** the partner's own verified identity attempts to claim that partner's link
- **THEN** the system rejects commission attribution without affecting the account's ordinary product access

### Requirement: Attribution is server authoritative and edition isolated
The system SHALL record qualified Global visits and bind a durable first-level partner attribution when a referred visitor later verifies a Global account within the configured window. Global attribution MUST NOT read or mutate Chinese users, links, orders or reward records.

#### Scenario: Referred visitor verifies an account
- **WHEN** a qualified visitor verifies a Global email account within the attribution window
- **THEN** the server binds the account to the eligible Global partner once using first-party evidence

#### Scenario: Browser fabricates a payment return
- **WHEN** a browser supplies a success URL or unverified provider reference
- **THEN** no partner commission or paid-customer metric is created

### Requirement: Commission follows confirmed Creem financial facts
The system SHALL create a 20% USD commission earning only from an eligible provider-confirmed Creem receipt attributed to a partner. Refunds, disputes and chargebacks MUST create append-only reversal entries, and duplicate or reordered provider events MUST remain idempotent.

#### Scenario: Eligible Creem order is confirmed
- **WHEN** a signed validated Creem event confirms an attributed eligible order
- **THEN** the system records one earning with the order, commission rule version, eligibility time and financial basis

#### Scenario: Confirmed order is refunded
- **WHEN** Creem later confirms a full or partial refund, dispute or chargeback
- **THEN** the system appends a capped commission reversal without deleting the original earning

#### Scenario: Creem checkout remains disabled
- **WHEN** Global commerce is not activated or no signed paid event exists
- **THEN** visits and registrations may be attributed but paid revenue and commission remain zero

### Requirement: Partners see private aggregate performance without referred-user identity
An enrolled partner SHALL see qualified visits, registrations, confirmed paid customers, attributed revenue, pending commission, available commission and settled commission. The response MUST NOT expose referred-user email, interview content, materials, screenshots or payment credentials.

#### Scenario: Partner opens the dashboard
- **WHEN** an enrolled partner opens the protected Global partner page
- **THEN** the service returns only that partner's aggregate metrics, balances, link and settlement history in English

### Requirement: Runtime pause preserves historical accounting
Disabling Global partner recruitment SHALL hide the homepage entry and block new enrollment while preserving existing links, attribution, earnings, reversals, payout profiles, settlement requests and operator reconciliation.

#### Scenario: Operator pauses recruitment
- **WHEN** an authorized Global operator confirms disabling the activity
- **THEN** new discovery and enrollment stop while existing partner financial history remains readable and settleable
