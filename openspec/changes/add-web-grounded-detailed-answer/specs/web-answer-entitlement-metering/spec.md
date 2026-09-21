## ADDED Requirements

### Requirement: Web answer rate and reservation

Domestic web-grounded detailed answers SHALL use the server-managed `web_answer` usage kind at 20 integer points per successful answer. The service SHALL reserve usage before creating the AI task and SHALL use the caller idempotency key when provided.

#### Scenario: Points user starts web answer
- **WHEN** an eligible user with enough available points requests a web answer
- **THEN** exactly 20 points SHALL be reserved and no second reservation SHALL be created for a repeated request with the same usage ID

#### Scenario: Insufficient points
- **WHEN** an ineligible user has fewer than 20 available points
- **THEN** the API SHALL return a recoverable 409 and SHALL not call the search or answer model

### Requirement: Seven-day membership entitlement

An active domestic time pass SHALL waive the 20-point charge only when its server-side catalog product has `duration_days >= 7`. One-day and three-day passes SHALL not waive web-answer points.

#### Scenario: Seven-day pass
- **WHEN** a user with an active seven-day, fifteen-day, or thirty-day pass requests a web answer
- **THEN** the usage SHALL be reserved with zero points and `billingSource=time_pass`

#### Scenario: Short pass
- **WHEN** a user with only an active one-day or three-day pass requests a web answer
- **THEN** the service SHALL reserve 20 points from the wallet

### Requirement: Settlement and release

The service SHALL settle a web-answer reservation only after a usable detailed answer is delivered, and SHALL release it on cancellation, timeout, provider failure, or unsuccessful answer generation.

#### Scenario: Successful completion
- **WHEN** a web-grounded detailed answer completes with usable text
- **THEN** the reservation SHALL become settled exactly once

#### Scenario: Failed completion
- **WHEN** search or model processing fails and no usable detailed answer is delivered
- **THEN** the reservation SHALL become released and points SHALL remain available
