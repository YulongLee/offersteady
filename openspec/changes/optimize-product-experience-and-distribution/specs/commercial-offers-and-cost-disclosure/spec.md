## ADDED Requirements

### Requirement: Published catalog uses the approved launch price ladder
The initial approved catalog SHALL offer 3-day membership at ¥69.90, 7-day membership at ¥129.90, 15-day membership at ¥219.90 and 30-day membership at ¥329.90. It SHALL offer 300 points at ¥39.90, 800 points at ¥89.90 and 2000 points at ¥199.90. Prices MUST come from a versioned server catalog and MUST NOT be trusted from client input.

#### Scenario: User opens the billing page
- **WHEN** the current catalog version is available
- **THEN** the page shows the exact server products, effective daily price or point unit price, applicable scope and catalog version

#### Scenario: Catalog price changes after order creation
- **WHEN** an existing unpaid or reviewable order was created from an earlier published catalog
- **THEN** the order retains its original product and amount snapshot while new orders use the new version

### Requirement: Membership scope and exclusions are explicit
An active membership SHALL preserve points for ordinary answers and screenshot answers within disclosed normal personal-use constraints. Knowledge document parsing and indexing SHALL remain point-billed and MUST be listed as excluded from membership.

#### Scenario: Member requests an ordinary answer
- **WHEN** the user has an active membership and creates an eligible ordinary answer task
- **THEN** the task records member usage and deducts zero points

#### Scenario: Member indexes a knowledge document
- **WHEN** an active 15-day or 30-day member still has a knowledge allowance
- **THEN** the system locks and consumes one allowance only after successful indexing; other members and exhausted allowances use points

### Requirement: Every point-consuming action is disclosed before confirmation
The billing page SHALL list welcome grants and current rates for ordinary answers, screenshot answers and knowledge indexing. An operation confirmation SHALL show its price, entitlement source and projected balance before creating the billable task.

#### Scenario: User views point consumption explanation
- **WHEN** the user opens the points section
- **THEN** it explains the 200-point welcome grant, 5-point ordinary answer, 15-point screenshot answer, 200-point knowledge minimum, per-1,000-Token rate and long-pass allowances

#### Scenario: Balance is insufficient for knowledge indexing
- **WHEN** the server estimate exceeds the user's available points
- **THEN** the system blocks the indexing task, preserves the uploaded document in a non-indexed state and presents purchase options

### Requirement: Knowledge indexing is estimated, reserved and settled idempotently
A document with usable text SHALL receive a server quote using `max(200, ceil(Token / 1000) × 20)`. The quote MUST require explicit confirmation. The system MUST reserve points or a long-pass allowance before processing, settle only after a usable index is delivered and release on failure or cancellation.

#### Scenario: Minimum-tier document indexes successfully
- **WHEN** the user confirms a 200-point quote and a usable index is delivered
- **THEN** exactly 200 points are settled once for that document version

#### Scenario: Unchanged document is submitted again
- **WHEN** the same user resubmits unchanged content or an indexing idempotency key is replayed
- **THEN** the system reuses the existing result or usage record without a second deduction

#### Scenario: Indexing fails after reservation
- **WHEN** parsing, embedding or index storage fails before a usable result exists
- **THEN** the system releases the full reservation and records a safe failure description without document content

### Requirement: Product publication is protected by unit economics
The catalog administration service SHALL reject publication of a product or rate whose conservative projected gross margin is below the configured threshold. Cost inputs SHALL exclude document and interview content.

#### Scenario: Proposed membership price fails margin policy
- **WHEN** estimated model, speech, storage, payment and support costs put the product below the margin threshold
- **THEN** the system keeps the product unpublished and records the non-content cost calculation for review

### Requirement: Redemption credits do not mutate the commercial catalog
Points credited from an authorized one-time redemption code SHALL enter the existing wallet without changing published product prices, usage rates, membership scope or margin-policy inputs. The client MUST NOT treat a redemption code as a catalog product or submit a trusted points amount.

#### Scenario: User redeems campaign points
- **WHEN** the server confirms a valid points-code redemption
- **THEN** the wallet receives the server-defined points while the current catalog version, product prices and AI usage rates remain unchanged
