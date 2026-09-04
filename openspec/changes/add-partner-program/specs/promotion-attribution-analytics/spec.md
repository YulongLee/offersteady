## ADDED Requirements

### Requirement: Partner links reuse promotion attribution facts
Partner links SHALL use the existing safe `/r/{slug}` redirect, qualified-visit filtering, first-party visitor identifier, registration claim and locked acquisition attribution. Link records SHALL distinguish partner ownership from operator campaigns without changing the meaning of existing campaign reports.

#### Scenario: Partner link receives a qualified visit
- **WHEN** a human visitor follows an active partner link and completes the existing qualification threshold
- **THEN** the visit is recorded by the existing promotion pipeline and is available to the owning partner only as an aggregate count

#### Scenario: Partner link collection fails
- **WHEN** the promotion queue is unavailable during redirect
- **THEN** the visitor still reaches the safe product destination and no product hot path waits for commission processing
