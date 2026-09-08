## ADDED Requirements

### Requirement: Global public routes MUST be independently readable
The Global site MUST return route-specific English title, description, canonical URL, H1, and substantive visible body content for every indexable public route without requiring client-side JavaScript.

#### Scenario: Crawler requests a public feature route
- **WHEN** a crawler directly requests `/features` or an approved `/features/*` route
- **THEN** the response contains that route's unique metadata, H1, body, and self-canonical rather than the homepage document

#### Scenario: Crawler requests a public hub or download route
- **WHEN** a crawler directly requests `/guides`, `/interview-questions`, or `/download`
- **THEN** the response contains a distinct, useful English document matching that route's search intent

### Requirement: Public content MUST preserve responsible-use boundaries
All new Global public content MUST describe AI output as guidance, require users to verify claims and use their real experience, and direct users to follow applicable interview-organiser rules.

#### Scenario: Public copy is released
- **WHEN** the build scans homepage, feature, hub, pricing, company, policy, and download content
- **THEN** responsible-use language is present and prohibited deceptive-use terms or unsupported outcome claims are absent

### Requirement: The international user manual MUST remain removed
The Global public navigation, footer, sitemap, GEO resources, and new public catalogue MUST NOT publish or promote a user-manual route.

#### Scenario: Global public navigation is rendered
- **WHEN** a visitor or crawler reads the homepage or another public page
- **THEN** no “User guide” navigation item or `/guide` search link is present

### Requirement: Public content MUST use verified product facts
The public content MUST contain only capabilities, prices, platform facts, privacy boundaries, operator information, and support details verified by the existing Global product contract.

#### Scenario: Paid checkout remains disabled
- **WHEN** Pricing or another public page mentions Weekly Pro or Monthly Pro before Creem activation
- **THEN** visible copy shows the approved prices with `Coming Soon` and no live checkout control or availability claim

