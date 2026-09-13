## ADDED Requirements

### Requirement: Public Global pages accurately expose live checkout
The Global homepage and pricing page SHALL state that approved live checkout is available and SHALL provide a sign-in entry point for each paid plan without creating an order anonymously.

#### Scenario: Anonymous visitor views a paid plan
- **WHEN** an anonymous visitor opens the Global homepage or `/pricing`
- **THEN** the page shows the current plan price and a link to the existing `/login` route, without disabled “provider approval” controls or stale unavailable-checkout language

#### Scenario: Authenticated visitor continues to checkout
- **WHEN** an authenticated visitor signs in and opens the Global billing page
- **THEN** the existing Creem Live checkout action remains available and uses the existing authenticated checkout API

#### Scenario: Public structured data is rendered
- **WHEN** a crawler reads the homepage or pricing JSON-LD
- **THEN** each paid offer describes its live purchase path and does not claim that checkout is unavailable
