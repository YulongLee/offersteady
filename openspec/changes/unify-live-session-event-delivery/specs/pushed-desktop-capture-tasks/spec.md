## ADDED Requirements

### Requirement: Push-first desktop capture delivery
The current desktop companion SHALL maintain a cancellable authenticated event subscription while it is bound to a live interview and SHALL start a remote screenshot task immediately after receiving a requested event addressed to that device.

#### Scenario: Web creates a screenshot task
- **WHEN** the web client creates a screenshot request for a connected current-version desktop companion
- **THEN** the companion receives the request through the device event stream without waiting for its next polling interval

#### Scenario: Companion is idle or unbound
- **WHEN** the desktop companion is not bound to a live interview
- **THEN** it does not maintain an active screenshot task subscription or query pending screenshot tasks at a live frequency

### Requirement: Safe fallback and reconnection
The desktop companion SHALL fall back to a single non-overlapping exponential-backoff query loop only when the push subscription cannot be established or becomes unhealthy, and SHALL stop fallback polling after push recovery.

#### Scenario: Event stream disconnects
- **WHEN** the device event stream fails during a live interview
- **THEN** the companion starts bounded fallback polling, reconnects the stream with backoff, and never runs overlapping task queries

#### Scenario: Event stream recovers
- **WHEN** the device event stream reconnects successfully
- **THEN** the companion cancels the fallback query timer and resumes push-first delivery

### Requirement: Idempotent task claiming
The backend and desktop companion SHALL use request identifiers and persisted request status to prevent duplicate capture, upload, answer generation, or billing when the same task is delivered more than once.

#### Scenario: Same request is redelivered
- **WHEN** a requested event is delivered twice or an old polling client races with a current push client
- **THEN** at most one active capture flow proceeds and terminal requests are not processed again

### Requirement: Backward compatibility for installed companions
The backend SHALL retain the existing pending-request query endpoint and its successful empty response semantics for older desktop companion versions.

#### Scenario: Older companion polls with no task
- **WHEN** an older registered companion queries for a pending capture while none exists
- **THEN** the backend returns a successful empty result without warning-level noise

#### Scenario: Older companion polls with a task
- **WHEN** an older companion is bound to a live session and a pending request exists
- **THEN** it can claim and complete the task through the existing endpoints
