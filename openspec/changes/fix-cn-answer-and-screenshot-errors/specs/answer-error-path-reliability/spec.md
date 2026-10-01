## ADDED Requirements

### Requirement: Stable insufficient-balance reservation contract
The persistent billing repository SHALL return only supported reservation fields and SHALL keep membership policy inputs separate from reservation results.

#### Scenario: Ordinary answer lacks available points
- **WHEN** a PostgreSQL-backed ordinary answer reservation has insufficient available points and a null minimum-pass policy
- **THEN** it SHALL return insufficient_balance without TypeError, charging points, or invoking the answer provider

#### Scenario: Streaming startup is denied
- **WHEN** the stream generator rejects billing or session eligibility before its first event
- **THEN** the API SHALL return the normal HTTP error envelope before sending SSE headers and SHALL release its executor slot and any unbound auto-answer claim

#### Scenario: Successful stream begins
- **WHEN** startup succeeds and the first event is available
- **THEN** that event SHALL be delivered exactly once in order with subsequent events, without waiting for the whole model answer

#### Scenario: Web answer lacks eligible pass and points
- **WHEN** a web answer requires a seven-day pass and the user has neither qualifying entitlement nor sufficient available points
- **THEN** it SHALL produce the existing recoverable billing error, not HTTP 500, and SHALL preserve the 20-point and seven-day rules

#### Scenario: Success and replay remain unchanged
- **WHEN** points or a qualifying pass cover a usage, or a reservation is replayed
- **THEN** reservation, idempotency, settlement, and release SHALL keep their existing behavior

### Requirement: Screenshot failure reporting cannot mask the original error
Screenshot background error handling SHALL call logging with the required arguments and SHALL retain privacy-safe original error classification without logging raw screenshot content, credentials, or exception messages.

#### Scenario: Upload or answer fails and recovery succeeds
- **WHEN** screenshot completion raises an error and its request can be marked failed
- **THEN** the wrapper SHALL finish without an uncaught logging error and SHALL preserve the existing failed phase and error classification

#### Scenario: Recovery or transition callback also fails
- **WHEN** failure-state persistence or its callback raises a second error
- **THEN** the wrapper SHALL record both error categories without a secondary logging TypeError

#### Scenario: Capture was cancelled
- **WHEN** a cancelled capture cannot be claimed during completion or failure recovery
- **THEN** it SHALL remain cancelled and SHALL not be revived or produce a logging TypeError

### Requirement: Domestic idle deployment
The release SHALL use the current running domestic backend as baseline, deploy only the scoped fixes after tests, and require no ongoing interviews before switching.

#### Scenario: An interview is active
- **WHEN** the pre-switch check detects a live interview or active audio
- **THEN** deployment SHALL wait without restarting the backend

#### Scenario: Idle release and verification
- **WHEN** the tested candidate passes an immediate idle check
- **THEN** only the backend SHALL be switched with its previous image retained for rollback and health verified afterward
