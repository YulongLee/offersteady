## ADDED Requirements

### Requirement: System audio recovery survives transient reopen failures
The companion SHALL retain a recovery supervisor outside the failed media runtime and SHALL retry system-audio acquisition with bounded backoff until recovery succeeds, capture stops, or the retry budget is exhausted.

#### Scenario: Headset removal ends the loopback track
- **WHEN** the system-audio track ends and the first reopen attempt fails during the operating-system route transition
- **THEN** the companion SHALL keep the publisher and microphone alive and retry system capture without user re-entry

#### Scenario: Recovery succeeds
- **WHEN** a later bounded attempt opens a healthy system track
- **THEN** the companion SHALL attach exactly one runtime and resume capture automatically

### Requirement: Recovery preserves transport identity and sequence
The companion SHALL preserve publisher identity and monotonically increasing channel sequence state across system-source recovery.

#### Scenario: Old frames are resent during recovery
- **WHEN** the transport retransmits an older sequence
- **THEN** diagnostics SHALL retain the highest sent sequence and the retry SHALL NOT reset the channel generation

#### Scenario: Shared transport requires replacement
- **WHEN** sequence recovery replaces the WebSocket transport while microphone and system media tracks are healthy
- **THEN** the companion SHALL keep both capture runtimes attached, pause publication, align to authoritative resume offsets, and resume without reopening media devices

#### Scenario: Resume offset includes an unacknowledged terminal
- **WHEN** a reconnect reports a resume offset at or beyond a queued terminal sequence but the companion has not received `terminal-accepted` for its terminal id
- **THEN** the companion SHALL retain and resend the terminal, and the Backend SHALL re-admit it unless that terminal is already accepted
- **AND** the visible transcript SHALL be eligible to advance to a provider-confirmed final instead of remaining recognition-incomplete

### Requirement: Recovery is bounded and observable
Recovery SHALL use metadata-only attempt, reason, outcome, and timing diagnostics and SHALL release timers and media resources on stop.

#### Scenario: Retry budget is exhausted
- **WHEN** all bounded attempts fail
- **THEN** only system audio SHALL become unavailable and no retry timer, media track, or raw audio SHALL persist

### Requirement: Removed headset microphones fall back automatically
When the selected microphone track ends or its capture watchdog reports loss, the companion SHALL stop targeting the removed device identity, acquire the operating-system default microphone with bounded retries, and preserve the system-audio runtime and publisher transport.

#### Scenario: Headset input disappears during an interview
- **WHEN** the selected headset microphone track ends while capture is active
- **THEN** the companion SHALL keep system audio publishing and automatically attach the current default microphone without requiring interview re-entry

#### Scenario: Virtual default route remains stale
- **WHEN** Chromium's virtual default microphone still references the removed headset
- **THEN** the companion SHALL exclude the ended device, try currently enumerated physical inputs with per-attempt timeouts, and close any stream that resolves after timeout

#### Scenario: User explicitly selects another microphone
- **WHEN** the user selects an available microphone during capture
- **THEN** recovery SHALL retain that requested device identity while applying bounded retries

### Requirement: Companion 1.1.8 is verifiable
The release SHALL identify version 1.1.8 and include automated macOS headset-removal coverage plus supported-platform packaging verification.

#### Scenario: Local acceptance build starts
- **WHEN** verified 1.1.8 is installed locally
- **THEN** the companion SHALL start successfully and expose metadata sufficient for a consented headset-removal test
