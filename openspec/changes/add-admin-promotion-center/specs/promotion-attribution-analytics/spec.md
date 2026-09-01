## ADDED Requirements

### Requirement: Promotion touchpoints use privacy-minimized first-party identity
The system SHALL use a random first-party anonymous visitor identifier for consented promotion attribution and MUST NOT use device fingerprinting, raw IP addresses, full user agents, full referrer URLs, phone numbers, access tokens, or interview content as attribution identifiers. Visitors who decline non-essential analytics MUST retain full access to redirect, registration, download, interview, and payment flows.

#### Scenario: Visitor accepts analytics attribution
- **WHEN** a visitor opens a promotion link with applicable analytics permission
- **THEN** the system stores a secure first-party anonymous identifier and only the allowlisted attribution fields required for reporting

#### Scenario: Visitor declines analytics attribution
- **WHEN** a visitor declines the optional persistent identifier
- **THEN** the redirect and product remain available and the system records at most a non-linkable aggregate hit

### Requirement: Anonymous identity binds deterministically after authentication
After successful registration or login, the system SHALL support an idempotent claim that binds eligible anonymous promotion touchpoints to the authenticated internal user. Claim failure MUST NOT fail authentication, and a pending claim MUST be safely retryable without creating duplicate registrations or attribution facts.

#### Scenario: Promoted visitor registers
- **WHEN** a visitor with an eligible promotion touchpoint completes registration
- **THEN** the system binds that visitor to the new user and computes acquisition attribution within the configured window

#### Scenario: Identity claim is retried
- **WHEN** a previous claim response was lost and the client retries the same claim
- **THEN** the system returns the same binding outcome without duplicating touchpoints or conversions

### Requirement: Acquisition attribution is stable and explainable
The system MUST compute versioned `first_touch` and `last_non_direct_touch` acquisition attribution from valid touchpoints within the configured attribution window. Once a user's acquisition attribution is locked at first registration, later visits MUST NOT silently replace it. Direct, organic, and unattributed outcomes MUST remain explicit.

#### Scenario: Visitor uses several promotion links before registering
- **WHEN** a visitor opens a 牛客 link and later a 小红书 link before registration within the attribution window
- **THEN** first-touch attributes acquisition to 牛客 and last-non-direct-touch attributes it to 小红书 under their respective model versions

#### Scenario: Existing user later opens a campaign link
- **WHEN** an already registered user with locked acquisition attribution opens a different promotion link
- **THEN** the system records an assisting touchpoint but does not rewrite the user's acquisition source

#### Scenario: No valid touchpoint exists
- **WHEN** a user registers without an eligible promotion touchpoint
- **THEN** the acquisition is reported as direct, organic, or unattributed according to explicit deterministic rules

### Requirement: Funnel stages use authoritative business facts
The promotion funnel MUST define visit from qualified visitors, registration from `auth_users`, download from an actual server download response, use from the first successfully started live interview, order from `billing_checkout_orders`, payment from a channel-authoritatively confirmed `paid` order, and revenue from the paid order amount. Analytics events MUST NOT manufacture or override these business facts.

#### Scenario: Checkout is created but not paid
- **WHEN** an attributed user creates an order that never reaches the authoritative paid state
- **THEN** the funnel counts the order stage but does not count payment or revenue

#### Scenario: User clicks download but no file response starts
- **WHEN** a visitor clicks a download control but the server does not begin returning an installation package
- **THEN** the UI interaction may be counted separately but the download funnel stage is not completed

### Requirement: Funnel conversion is cohort-based and deduplicated
The default funnel SHALL use visitors whose first qualified promotion visit falls within the selected acquisition range and SHALL observe downstream stages within the attribution window. Each stage MUST count a visitor or user at most once, MUST show stage and cumulative conversion rates, and MUST mark recent cohorts as observing until their window matures.

#### Scenario: One user creates several interviews and orders
- **WHEN** one attributed user starts multiple interviews and creates multiple orders
- **THEN** the person appears once in registration and use funnel stages while order count and revenue remain available as separate metrics

#### Scenario: Recent cohort is incomplete
- **WHEN** the selected acquisition cohort has not reached the end of its observation window
- **THEN** the funnel displays an observing state and does not present current drop-off as a final mature result

### Requirement: A conversion is not double-attributed
The system MUST materialize attribution facts with a uniqueness boundary covering conversion type, authoritative source record, and attribution model version. Within one model, one registration, activation, order, or paid order MUST contribute to at most one link, campaign, and channel path.

#### Scenario: Aggregation job is rerun
- **WHEN** the attribution and snapshot jobs process the same paid order more than once
- **THEN** the resulting paid order and revenue are counted exactly once for each attribution model version

### Requirement: Promotion overview exposes decision-ready metrics
The promotion overview SHALL provide qualified visits, unique visitors, registrations, activated users, paying users, paid orders, attributed paid revenue, entered cost, registration rate, activation rate, payment rate, CAC, ROAS, and ROI for the selected time range and attribution model. The report MUST state timezone, generation time, data freshness, attribution coverage, excluded traffic, and metric definitions.

All operator-facing metric names, states, table headers, and funnel labels in the Chinese administration console SHALL be rendered in Chinese; stable API field names MAY remain language-neutral and MUST NOT be exposed directly as user-facing labels.

#### Scenario: Administrator views today's promotion result
- **WHEN** an administrator selects today
- **THEN** the overview shows bounded near-real-time totals with a freshness timestamp and keeps historical daily snapshots separate from incomplete current-day values

#### Scenario: Revenue is available but cost coverage is partial
- **WHEN** some links in the selected range have no cost records
- **THEN** the overview marks cost-derived metrics as partial and does not imply complete profitability

#### Scenario: Administrator reads promotion detail tables
- **WHEN** the Chinese administration console renders channel, campaign, link, health, or attribution metadata
- **THEN** it displays Chinese labels and readable localized states instead of raw API keys or English enum values

### Requirement: Reports compare campaigns, channels, and links consistently
The system SHALL support the same date range, attribution model, timezone, bot filter, and metric definitions across campaign, channel, and link reports. Aggregating mutually exclusive rows under the same model MUST reconcile to the overview totals except for explicitly labeled direct, organic, or unattributed buckets.

#### Scenario: Administrator compares platforms
- **WHEN** an administrator compares 牛客、小红书、百度 and 抖音 for one range
- **THEN** every row uses the same denominators and exposes visits, registration, activation, payment, revenue, cost, CAC, and ROAS with coverage labels

#### Scenario: Administrator opens one content link
- **WHEN** an administrator opens a specific 小红书笔记 link report
- **THEN** the report shows only that link's valid visitors and uniquely attributed downstream conversions

### Requirement: Analytics are isolated from product hot paths
Promotion event delivery, identity claim, attribution computation, snapshot aggregation, and management queries MUST NOT add synchronous remote calls to registration, live interview, ASR, quick answer, screenshot answer, checkout, or payment confirmation paths. Collection failure MUST degrade analytics coverage rather than product availability.

#### Scenario: Promotion analytics storage is unavailable during an interview
- **WHEN** the promotion queue, worker, or snapshot database operation is unavailable
- **THEN** the ongoing interview and AI answer continue normally and the promotion report marks delayed or partial coverage

### Requirement: Promotion data retention and deletion are enforceable
The system MUST define retention for raw touchpoints and long-lived aggregate snapshots, MUST remove or irreversibly detach user-linked promotion bindings when the corresponding account deletion is completed, and MUST preserve only non-identifying aggregates thereafter. Management reports MUST NOT expose visitor IDs, user IDs, phone numbers, or individual browsing timelines.

#### Scenario: User account deletion completes
- **WHEN** an account deletion workflow removes a user's product data
- **THEN** promotion identity bindings and user-linked conversion facts are deleted or irreversibly detached while aggregate channel totals remain non-identifying

### Requirement: Metric and attribution coverage is explicit
Every promotion report MUST return its attribution model and version, coverage start, freshness state, unattributed count, excluded-bot count, and cohort maturity. Missing or unavailable values MUST remain null or explicitly unavailable and MUST NOT be rendered as zero.

#### Scenario: Historical orders predate promotion tracking
- **WHEN** the system displays a date before reliable promotion touchpoints existed
- **THEN** those orders are marked unattributed or unavailable and are not assigned to a generated link or campaign
