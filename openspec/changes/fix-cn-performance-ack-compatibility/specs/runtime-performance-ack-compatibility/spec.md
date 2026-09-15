## ADDED Requirements

### Requirement: Accept existing performance acknowledgement fields
The performance acknowledgement endpoint SHALL accept the existing optional route, executor admission and generator start timestamps, preserve them in content-free diagnostics, and remain compatible when omitted or null.

#### Scenario: New client submits entry timing
- **WHEN** an authorized client submits routeReceivedAtMs, executorAdmittedAtMs and answerGeneratorStartedAtMs
- **THEN** the real route and service return accepted without a TypeError and preserve the three timestamp values

#### Scenario: Legacy client omits timing
- **WHEN** an authorized client omits the three entry timing fields or sends null
- **THEN** the request succeeds and diagnostics do not invent timestamps

### Requirement: Preserve ownership and metadata boundaries
The endpoint MUST retain session ownership checks, forbid unknown content fields, and avoid invoking an answer model or changing session state for telemetry acknowledgement.

#### Scenario: Unauthorized session acknowledgement
- **WHEN** a caller does not own the target session
- **THEN** acknowledgement is denied and no diagnostic record is added

#### Scenario: Request includes private content
- **WHEN** a performance acknowledgement contains a question or transcript field outside the metadata allowlist
- **THEN** request validation rejects it

### Requirement: Repair the deployed baseline without unrelated replacement
The repair SHALL be validated against the running Chinese Backend source and its exact image, MUST preserve a rollback image, and MUST NOT replace any unrelated runtime source or other service.

#### Scenario: Production repair is released
- **WHEN** regression and isolated candidate-image verification pass and there is no live interview or active audio workload
- **THEN** only the repaired Backend image is activated with the same production configuration and health is checked
