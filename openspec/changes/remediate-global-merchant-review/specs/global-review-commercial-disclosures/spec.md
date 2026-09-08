## ADDED Requirements

### Requirement: Accurate commercial plans and checkout status
Public pricing SHALL retain the authoritative Free and four paid prices, accurately describe included benefits, one-time versus recurring billing, fulfillment and access start. Paid controls SHALL remain disabled without creating payments. Copy SHALL state merchant approval and production configuration are required for live checkout, without claiming approval or an ongoing review.

#### Scenario: Reviewer examines paid plans
- **WHEN** Pricing is read in a browser or directly over HTTP
- **THEN** the reviewer sees $9.99/24 hours, $49.99/7 days, $99.99/month and $199.99/90 days with correct billing/access terms and approval-dependent unavailable checkout
- **AND** no Coming Soon or demo-only payment language remains in public output

### Requirement: Complete consistent service and policy disclosures
Home, Terms, Privacy, Refund, About and Contact SHALL clearly identify the service and required operator/support details. Terms SHALL cover all fifteen requested topics; Privacy SHALL describe actual processing without unsupported security or erasure claims; Refund SHALL provide effective date, eligibility, procedure, processing, exceptions and contact without promising unconditional refunds.

#### Scenario: Reviewer follows the disclosure pages
- **WHEN** Home, Pricing, About, Contact, Terms, Privacy and Refund are reviewed
- **THEN** support uses contact@oneshowailab.com and the operator is 杭州临平知界智能技术工作室（个体工商户）, Hangzhou, China
- **AND** users remain responsible for verified answers and compliance with organizer policies

### Requirement: Static parity and isolation
Each public review URL SHALL preserve its unique metadata, canonical, H1 and body in direct HTTP output. Required footer links and legal operator SHALL be visible. No login, payment API, AI, database or China behavior SHALL change.

#### Scenario: Non-JavaScript request
- **WHEN** a client requests a built review URL
- **THEN** it returns HTTP 200 with its own updated content and coherent metadata, robots and sitemap

#### Scenario: Regression checks
- **WHEN** existing Global tests and builds run
- **THEN** product workflows remain intact and keyword auditing distinguishes public claims from test/guard strings and historical records
