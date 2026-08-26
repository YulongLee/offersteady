## ADDED Requirements

### Requirement: Replacement recovery separates readiness from audio progress
The companion SHALL treat the current replacement WebSocket's authoritative connection state as transport readiness, SHALL wait for newly produced media before applying an audio acknowledgement deadline, and MUST NOT create another publisher solely because the source remains silent.

#### Scenario: Replacement connects while system audio is silent
- **WHEN** a replacement publisher receives the authoritative connection state and no audio frame is produced during the former ACK timeout window
- **THEN** the companion keeps that transport ready without creating another publisher
- **AND** delivery health remains recovering or waiting-for-audio rather than healthy

#### Scenario: Replacement receives fresh audio acknowledgement
- **WHEN** the current replacement transport sends a newly produced frame and receives its authoritative acknowledgement
- **THEN** recovery completes and delivery health becomes healthy
- **AND** events from superseded transports cannot complete recovery

#### Scenario: Backend retains the prior session offset across Publisher replacement
- **WHEN** the replacement connection reports a resume offset from the prior Publisher identity
- **THEN** the companion aligns its next produced sequence to the authoritative offset plus one before capture restarts
- **AND** it does not restart at zero and enter a sequence-gap loop

#### Scenario: Replacement sends audio without acknowledgement
- **WHEN** newly produced media is sent on the current replacement and no acknowledgement arrives within the delivery deadline
- **THEN** the companion stops that attempt before performing a bounded retry
- **AND** it never runs more than one recovery concurrently

### Requirement: Production recovery has no false HTTP fallback
The production companion MUST use the supported WebSocket v2 publisher path for automatic audio delivery and SHALL NOT claim successful fallback to a disabled or unauthenticated legacy HTTP frame route.

#### Scenario: Replacement retry budget is exhausted
- **WHEN** all bounded replacement WebSocket attempts fail to acknowledge newly produced audio
- **THEN** the companion stops automatic upload recovery, clears unrecoverable buffered PCM and reports terminal lost delivery
- **AND** it does not POST frames to the disabled legacy HTTP route

### Requirement: Capture health follows delivery evidence
The companion and live workspace SHALL derive delivery health from current capture, produced-frame, send, acknowledgement and buffer progress, and MUST NOT display normal capturing while produced audio cannot reach the Backend.

#### Scenario: Local system capture continues after acknowledgements stop
- **WHEN** worklet and system-audio frame counters advance but a produced or sent frame remains unacknowledged beyond the deadline
- **THEN** the companion and Web workspace display degraded, recovering or lost state
- **AND** they do not continue showing normal capture based only on the live interview command

#### Scenario: Terminal failure requires explicit recovery
- **WHEN** bounded automatic recovery is exhausted
- **THEN** health remains lost until the user explicitly restarts or rebinds the companion and a fresh frame is acknowledged

### Requirement: Stream bootstrap is bounded and current-state focused
The Backend SHALL deliver an initial realtime snapshot from authoritative current runtime, transcripts, candidates, cursor and required latest stateful events without loading the complete retained event history on the critical entry path.

#### Scenario: User enters or refreshes a live interview
- **WHEN** the Web client opens the realtime stream for an owned active session
- **THEN** the first snapshot contains enough current state to render the workspace and resume from its cursor
- **AND** retained historical event enumeration is not required before the first snapshot is sent

### Requirement: Partial subtitles remain monotonic and visible
The realtime delivery path SHALL deliver non-final partial transcript revisions and SHALL update a segment in place monotonically so an older revision cannot erase or overwrite newer visible text.

#### Scenario: Multiple partial revisions arrive before a browser flush
- **WHEN** several revisions for the same segment arrive in one delivery turn
- **THEN** the newest revision remains visible without waiting for the final transcript
- **AND** a later final revision replaces the partial in the same segment position

### Requirement: Desktop recovery correction is released as patch 1.1.3
The corrected companion SHALL use version 1.1.3 while retaining bundle identifier `com.offersteady.companion` and realtime protocol version `2.0`.

#### Scenario: Local joint-test build is prepared
- **WHEN** the implementation passes its focused regression suites, type checks and production build
- **THEN** a local 1.1.3 application is installed and launched for controlled system-audio testing
- **AND** no public production manifest is changed by the local test step

#### Scenario: Commercial release is later published
- **WHEN** real-device recovery and latency gates pass and the release is authorized
- **THEN** compatible Backend/Web changes are deployed before signed desktop artifacts and the public manifest are updated
