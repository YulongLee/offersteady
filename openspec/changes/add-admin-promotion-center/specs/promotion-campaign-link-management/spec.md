## ADDED Requirements

### Requirement: Administrators manage promotion channels
The system SHALL allow an administrator with `promotion.manage` permission to create, name, order, activate, and deactivate promotion channels. Channel identifiers used by historical touchpoints MUST remain stable, and deactivation MUST NOT delete historical analytics.

#### Scenario: Administrator creates a channel
- **WHEN** an authorized administrator creates the “小红书” channel with a unique code
- **THEN** the channel becomes available for new campaigns and links and the action is recorded in the management audit log

#### Scenario: Administrator deactivates a channel
- **WHEN** an authorized administrator deactivates a channel that has historical links and conversions
- **THEN** the system prevents new active links from using it while retaining all historical channel metrics

### Requirement: Administrators manage marketing campaigns
The system SHALL allow an administrator with `promotion.manage` permission to create and manage campaigns with a name, objective, status, start time, end time, optional budget, and notes. Campaign status MUST use `draft`, `active`, `paused`, or `ended` and MUST be evaluated independently from the status of each link.

#### Scenario: Campaign groups links from several platforms
- **WHEN** the administrator associates 牛客、小红书 and 抖音 links with “2026秋招推广”
- **THEN** the campaign page aggregates those links while each link retains its own channel attribution

#### Scenario: Campaign is paused
- **WHEN** an active campaign is paused
- **THEN** its links follow the configured pause policy and the system retains previous visits and conversions without rewriting them

### Requirement: Every promotion content item can have a dedicated link
The system SHALL create a dedicated promotion link with a non-enumerable slug, content name, channel, optional campaign, allowlisted internal destination, status, and creation metadata. Once a link has a valid touchpoint, its channel and campaign attribution MUST be immutable; correction SHALL use a cloned link.

#### Scenario: Administrator creates an article link
- **WHEN** an administrator creates a link for a specific 牛客 article under “2026秋招推广”
- **THEN** the system returns a stable copyable URL whose analytics are isolated from all other content links

#### Scenario: Administrator attempts to reclassify a used link
- **WHEN** a link already has a qualified visit and an administrator changes its channel or campaign
- **THEN** the system rejects the attribution change and offers cloning as the safe correction path

### Requirement: Promotion redirects are safe and fail open for product access
The public redirect endpoint MUST accept only stored active slugs and MUST redirect only to server-allowlisted internal destinations. Analytics delivery failure MUST NOT prevent the visitor from reaching the product. Unknown, expired, or disabled links MUST use a safe fallback and MUST NOT reveal internal identifiers.

#### Scenario: Active link redirects successfully
- **WHEN** a visitor opens an active promotion URL
- **THEN** the system assigns first-party anonymous identifiers, queues a minimal redirect event, and redirects to the configured internal destination

#### Scenario: Analytics queue is unavailable
- **WHEN** the event queue cannot accept a redirect event
- **THEN** the visitor is still redirected and the system records only a safe operational failure counter

#### Scenario: Malicious destination is supplied
- **WHEN** an administrator or request attempts to use an external or non-allowlisted redirect destination
- **THEN** the system rejects the destination and does not create an open redirect

### Requirement: Link analytics distinguish raw hits from qualified visits
The system MUST record raw redirect hits separately from qualified visits and MUST use qualified unique visitors as the default funnel denominator. Known bots, platform previews, administrator previews, and configured internal traffic MUST be excluded from qualified conversion reporting while remaining visible as aggregate exclusion counts.

#### Scenario: Social platform previews a link
- **WHEN** a known preview crawler requests a promotion URL without completing the landing-page qualification signal
- **THEN** the system counts a raw hit, excludes it from qualified visitors, and does not create a registration funnel entrant

#### Scenario: Real visitor loads the landing page
- **WHEN** a non-excluded browser reaches the destination and completes the page visibility qualification
- **THEN** the system records an idempotent qualified visit and includes the anonymous visitor once in unique visitor metrics

### Requirement: Promotion costs are append-only and auditable
The system SHALL allow only administrators with `promotion.cost.manage` permission to add dated CNY cost entries at campaign, channel, or link scope. Corrections MUST use an explicit reversing entry; the system MUST NOT overwrite historical cost totals.

#### Scenario: Administrator records campaign spend
- **WHEN** an authorized administrator records a 1,000 CNY cost for a campaign date
- **THEN** campaign cost, CAC, ROAS, and ROI include that entry and the audit log records the actor and reason

#### Scenario: Cost has not been entered
- **WHEN** a report has attributed revenue but no applicable cost entry
- **THEN** CAC, ROAS, and ROI display “成本未录入” rather than zero or infinity

### Requirement: Promotion management is permissioned and audited
The system MUST enforce `promotion.read`, `promotion.manage`, and `promotion.cost.manage` independently. Creation, update, clone, activation, deactivation, cost entry, and cost reversal MUST produce management audit events without storing credentials or visitor identifiers.

#### Scenario: Read-only operator opens promotion center
- **WHEN** an administrator has `promotion.read` but not management permissions
- **THEN** the administrator can view aggregate reports but cannot modify channels, campaigns, links, or costs
