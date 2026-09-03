## ADDED Requirements

### Requirement: A desktop device has one admitted screenshot stream
The Backend MUST admit at most one active screenshot capture-request SSE for a desktop device and MUST reject duplicates before binding lookup, Redis blocking waits, or screenshot processing begins.

#### Scenario: Duplicate stream overlaps a healthy stream
- **WHEN** a second screenshot stream request for the same device arrives while the first lease is active
- **THEN** the second request receives a bounded legacy-compatible retry response and does not consume an event-wait or control-executor task

#### Scenario: Different devices connect concurrently
- **WHEN** distinct valid desktop devices open screenshot streams
- **THEN** each device can hold one independent stream up to the configured global capacity

### Requirement: Screenshot stream admission is bounded
The Backend MUST bound rapid sequential reconnects and total active screenshot streams, and denied requests MUST complete with O(1) admission work without accumulating blocking Redis waits.

#### Scenario: One faulty device reconnects continuously
- **WHEN** one device repeatedly opens or closes screenshot streams above the configured window
- **THEN** accepted work remains bounded and subsequent attempts receive a retry response without starving ordinary APIs

#### Scenario: Global screenshot capacity is reached
- **WHEN** the configured active screenshot stream capacity is exhausted
- **THEN** a new stream is denied before event-wait submission while existing streams, realtime audio, and ordinary APIs continue

### Requirement: Screenshot waits are isolated from realtime delivery
Screenshot capture-request blocking waits MUST use resources independent from realtime transcript/session stream waits and short control operations.

#### Scenario: Screenshot reconnect storm occurs during an interview
- **WHEN** an abusive screenshot client retries while another user has an active audio publisher and transcript stream
- **THEN** screenshot work cannot exhaust the realtime event-wait executor or realtime control executor

### Requirement: Reconnect containment preserves screenshot correctness
Admission and retry containment MUST preserve pending-request lookup, cursor replay, screenshot upload, answer generation, and exactly-once billing semantics.

#### Scenario: A screenshot request occurs during reconnect
- **WHEN** a request is created after one stream disconnects and before its replacement is admitted
- **THEN** the replacement stream emits the pending request or its replayed event without losing it

#### Scenario: Duplicate stream is denied
- **WHEN** a duplicate stream receives an admission denial
- **THEN** it does not claim a request, upload a screenshot, start answer generation, or deduct points

### Requirement: Existing product behavior and clients remain compatible
The change MUST preserve current public routes and the behavior of supported and legacy companions without changing audio, ASR, subtitles, quick answers, screenshot answers, billing, permissions, prompts, or UI.

#### Scenario: Normal companion completes a screenshot answer
- **WHEN** a supported companion maintains one screenshot stream and receives a capture request
- **THEN** the request, upload, generated answer, progress events, and billing outcome match the baseline behavior

#### Scenario: Legacy companion receives a retry response
- **WHEN** a legacy companion creates a duplicate stream
- **THEN** its existing failure backoff can reconnect later without requiring a client upgrade or displaying a new user-facing workflow

### Requirement: Storm protection is observable without user content
The Backend MUST expose aggregate active, accepted, denied, released, and saturation counters and MUST NOT expose audio, transcript, screenshot, question, answer, manual-code, IP, or raw device identity data.

#### Scenario: Operator reviews a contained storm
- **WHEN** duplicate and rate admission controls activate
- **THEN** aggregate metrics show the protection activity without identifying the user or revealing product content

### Requirement: Production rollout preserves a rollback baseline
The Backend change MUST be switched only after active interviews and active audio publishers are zero, and the previous image and runtime data MUST remain available for immediate rollback.

#### Scenario: Production has active realtime usage
- **WHEN** the rollout check reports any active interview or active audio publisher
- **THEN** the deployment waits and does not replace the Backend

#### Scenario: Post-deployment regression occurs
- **WHEN** health, screenshot delivery, audio, subtitles, answers, billing, or latency fails its acceptance gate
- **THEN** production returns to the recorded baseline image without deleting Redis or PostgreSQL data
