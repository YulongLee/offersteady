## ADDED Requirements

### Requirement: Connected realtime transport suppresses fallback snapshots

The live web client SHALL consider an authenticated SSE response with a readable body transport-connected before the first application snapshot is rendered, and SHALL not run parallel fallback snapshot requests while that transport remains connected.

#### Scenario: Initial snapshot is slow
- **WHEN** the SSE response is accepted but the authoritative initial snapshot takes time to arrive
- **THEN** the client waits for the stream snapshot and does not request transcripts, candidates, events, and runtime in parallel

#### Scenario: Transport closes
- **WHEN** a previously connected SSE transport closes without a terminal session event
- **THEN** the client marks it unhealthy and schedules bounded recovery

### Requirement: Recovery polling is bounded and non-overlapping

The live web client SHALL use exponential backoff for degraded-mode snapshot reconciliation, SHALL keep at most one snapshot and one subscription attempt in flight, and SHALL stop recovery after SSE transport recovery.

#### Scenario: Subscription is pending
- **WHEN** an SSE subscription request is already active
- **THEN** the fallback scheduler does not create another snapshot or subscription request

#### Scenario: Repeated outage
- **WHEN** the stream remains unavailable across multiple attempts
- **THEN** recovery delays increase from the initial bounded delay to a capped delay without one-second request amplification

### Requirement: Realtime snapshot operations do not block the async event loop

High-frequency realtime HTTP routes SHALL execute synchronous service and repository work outside the FastAPI event loop while preserving authentication, ownership, response, and error semantics.

#### Scenario: Snapshot reads overlap a heartbeat
- **WHEN** runtime, transcript, candidate, and event reads are executing while another client sends a heartbeat
- **THEN** synchronous repository waits do not block the heartbeat coroutine on the event loop

### Requirement: Existing product behavior remains unchanged

The optimization MUST preserve explicit answer controls, transcript ordering, screenshot lifecycle, session lease replacement, pause/resume semantics, and billing behavior.

#### Scenario: User continues a normal interview
- **WHEN** the stream is healthy and the user speaks, pauses capture, requests a quick answer, or requests a screenshot answer
- **THEN** the visible and billable behavior remains the same while recovery traffic stays inactive
