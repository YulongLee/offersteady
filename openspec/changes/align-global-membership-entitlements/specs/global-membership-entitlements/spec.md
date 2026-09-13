## ADDED Requirements

### Requirement: Global billing state is isolated from domestic points
国际服 SHALL use Global Commerce as the billing source and MUST NOT display or mutate domestic points, domestic ledger, redemption codes, or domestic payment channels.

#### Scenario: Global user opens billing page
- **WHEN** a user on the global edition opens the billing page
- **THEN** the page requests Global Commerce state/catalogue and displays global plans, subscription status, and included usage without a domestic points balance

#### Scenario: Chinese edition remains unchanged
- **WHEN** a user on the Chinese edition opens the billing page
- **THEN** the existing domestic billing state and payment flow remain available without Global Commerce fields being required

### Requirement: Membership remaining time is visible and authoritative
The system SHALL return the active entitlement end time, subscription period end, renewal status, and queued entitlement information when available. The UI SHALL display remaining time and absolute expiry using server-provided timestamps.

#### Scenario: Active paid membership
- **WHEN** an authenticated global user has an active entitlement
- **THEN** the billing page shows the plan name, remaining duration, expiry time, and whether the subscription will renew or has been canceled

#### Scenario: Membership expires while page is open
- **WHEN** the displayed entitlement reaches its server-provided end time
- **THEN** the UI refreshes Global Commerce state and updates the available features and remaining time

### Requirement: Paid answer and screenshot usage is included
Paid global entitlements SHALL authorize realtime answer minutes and screenshot answers without domestic point deductions. Free entitlements SHALL retain their finite configured allowances.

#### Scenario: Paid member uses screenshot answer
- **WHEN** an active paid global member submits a screenshot answer
- **THEN** the request is authorized through Global entitlement reservation and no domestic points ledger entry is created

#### Scenario: Free user exhausts screenshot allowance
- **WHEN** a Free user has used all configured screenshot allowances
- **THEN** another screenshot answer is denied with an upgrade/allowance message and no negative points balance is created

### Requirement: Knowledge quota is tiered by plan
Global plan versions SHALL expose a knowledge Token allowance. The published commercial tiers SHALL provide 0 Token for the 1-day pass, 50,000 Token for the 7-day plan, 200,000 Token for the 30-day plan, and 1,000,000 Token for the 90-day plan.

#### Scenario: One-day member uploads knowledge material
- **WHEN** a 1-day member requests a knowledge upload quote
- **THEN** the quote is denied as not included and no quota is reserved

#### Scenario: Thirty-day member has remaining quota
- **WHEN** a 30-day member uploads material whose normalized text estimate fits within remaining quota
- **THEN** the system reserves the estimated Token amount and reports the remaining quota without using domestic points

#### Scenario: Upload indexing fails
- **WHEN** a reserved knowledge upload fails, is canceled, or expires
- **THEN** the reserved Token amount is released and the member's used quota is unchanged

#### Scenario: Quota is exhausted
- **WHEN** a member's normalized Token estimate exceeds the remaining quota
- **THEN** the upload is rejected before indexing and no quota or points are consumed

### Requirement: Historical entitlements preserve purchased benefits
The system SHALL store plan and quota values in the entitlement snapshot so that later catalogue edits do not change already purchased rights.

#### Scenario: Catalogue version changes
- **WHEN** an administrator publishes a new Global plan version
- **THEN** existing entitlements continue to use their stored duration and knowledge quota while new purchases use the new version

### Requirement: Global usage remains fair-use protected
Included or unlimited paid usage SHALL remain subject to existing server-side fair-use, concurrency, and abuse controls without exposing domestic points as a workaround.

#### Scenario: Excessive parallel usage
- **WHEN** a global account triggers an existing fair-use restriction before starting another interview
- **THEN** the new interview is denied while an already active interview is not interrupted
