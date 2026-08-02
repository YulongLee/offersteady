# Admin-managed billing catalog

## ADDED Requirements

### Requirement: Fixed commercial benefit tiers

The system SHALL expose time passes for exactly 1, 3, 7, 15, and 30 days and point packs for exactly 1,000, 3,000, 10,000, 30,000, and 66,666 points.

#### Scenario: User loads the billing page

- **WHEN** billing state is requested
- **THEN** only published products from the server catalog are returned
- **AND** every product matches an approved fixed benefit tier

### Requirement: Controlled price administration

The system SHALL let an authorized administrator update display name, price, and publication state without changing benefit quantity.

#### Scenario: Finance administrator changes a price

- **WHEN** a finance or super administrator submits a confirmed, recently authenticated, idempotent update with a reason
- **THEN** the price is persisted with a new catalog version
- **AND** an audit event is recorded

#### Scenario: Unauthorized administrator attempts a change

- **WHEN** an administrator without `catalog.manage` submits an update
- **THEN** it is rejected and no catalog row changes

### Requirement: Historical order isolation

The system SHALL use the product snapshot and amount captured when an order was created.

#### Scenario: Price changes after checkout creation

- **WHEN** a price changes after an order is created
- **THEN** that order retains its original amount and benefit snapshot
- **AND** new orders use the updated values
