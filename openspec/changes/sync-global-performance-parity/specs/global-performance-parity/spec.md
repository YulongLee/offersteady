## ADDED Requirements

### Requirement: Global web heartbeats use a lightweight authoritative projection

The Global backend MUST evaluate a normal web heartbeat using one authoritative session projection containing only the session identity, owner, lifecycle status, start time, and last activity time. It MUST NOT perform material, conversation, resume, billing, or full-session reads on the normal heartbeat path.

#### Scenario: Active session heartbeat

- **WHEN** an active session sends a valid web heartbeat
- **THEN** the service refreshes the activity lease and returns the existing successful heartbeat response
- **AND** the repository performs no material/session-detail read beyond the five-field projection

#### Scenario: Ended or expired session heartbeat

- **WHEN** the projection reports an ended or expired session
- **THEN** the service preserves the existing conflict response and does not report the session as active

### Requirement: Desktop heartbeats bound unchanged durable writes

The Global backend MUST persist first registration and material desktop-device changes immediately. For unchanged online heartbeats it MUST skip durable writes when the elapsed time is below the configured minimum interval, while returning a caller-visible device state with a fresh `last_seen_at_ms`. The effective interval MUST be no greater than half the heartbeat TTL.

#### Scenario: Unchanged heartbeat inside the interval

- **WHEN** the same online device sends an unchanged heartbeat before the minimum interval elapses
- **THEN** the service returns an online device view with the current timestamp
- **AND** it does not issue a durable repository write

#### Scenario: Material change or first registration

- **WHEN** a device is first registered or its display name, capabilities, or status changes
- **THEN** the service persists the update immediately

### Requirement: Global P95 diagnostics remain decomposable

The Global capacity response MUST continue to expose `requestBreakdown`, `userApiP95Ms`, `telemetryP95Ms`, and `slowRoutes`, with telemetry routes classified separately from user routes.

#### Scenario: Capacity sample with telemetry traffic

- **WHEN** the capacity sampler receives mixed user and telemetry requests
- **THEN** the response keeps separate P95 values and route lists so an operator can identify the true slow path

### Requirement: Global rollout preserves existing clients and is gated

The performance release MUST preserve existing API and companion protocols, MUST pass focused regression tests and static checks, and MUST be deployed only after the Global idle gate reports no live interviews, leases, active audio, unfinished tasks, or running material jobs.

#### Scenario: Safe Global deployment

- **WHEN** the candidate passes self-tests and two consecutive idle gates are clear
- **THEN** only the Global backend is updated and health/config/capacity checks pass
- **AND** the previous backend image remains available for rollback
