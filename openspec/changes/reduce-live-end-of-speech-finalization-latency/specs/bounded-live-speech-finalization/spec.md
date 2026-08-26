## ADDED Requirements

### Requirement: Noise-resilient microphone end-of-speech detection
The desktop companion SHALL use an adaptive ambient threshold and bounded turn-envelope release rule so residual microphone energy cannot keep an utterance active indefinitely after speech returns toward the ambient range.

#### Scenario: Loud speech returns to steady residual noise
- **WHEN** a microphone utterance contains confirmed speech and its energy then drops to a steady residual level below the bounded turn-envelope release threshold
- **THEN** the companion SHALL emit a silence terminal frame within 1.5 seconds without waiting for the maximum-turn deadline

#### Scenario: Speech resumes during the tail window
- **WHEN** confirmed microphone speech resumes before the tail deadline
- **THEN** the companion SHALL keep the same segment active and SHALL NOT emit a premature terminal frame

#### Scenario: Continuous speech reaches the hard boundary
- **WHEN** microphone speech remains continuously active without a qualifying release interval
- **THEN** the companion SHALL emit a max-duration terminal frame at the configured bounded maximum

### Requirement: Every visible partial reaches a terminal presentation
The realtime service SHALL ensure that every partial transcript published to the session event stream is followed by a monotonic provider-final or incomplete terminal update within a bounded recovery interval.

#### Scenario: Provider final is intentionally suppressed
- **WHEN** a visible partial has a final provider result suppressed as empty, filler, repetitive, or duplicate
- **THEN** the backend SHALL publish a terminal transcript update preserving the last stable visible text without triggering context, answers, usage duplication, or billing

#### Scenario: A newer segment supersedes an unfinished segment
- **WHEN** a new partial segment arrives on a source that still tracks a different unfinished segment
- **THEN** the backend SHALL publish an incomplete terminal update for the superseded segment without closing the healthy source connection

#### Scenario: No terminal frame arrives
- **WHEN** an active source turn receives no new frame for four seconds
- **THEN** the backend SHALL terminalize it as incomplete and recover only the affected ASR source

### Requirement: Bounded web stale presentation
The live conversation UI SHALL stop presenting a partial as actively transcribing after four seconds without a newer revision while preserving the distinction between incomplete and provider-final text.

#### Scenario: Partial revision becomes stale
- **WHEN** a non-final transcript has received no newer revision for four seconds
- **THEN** the UI SHALL stop its active caret and display the segment as recognition incomplete

#### Scenario: Final revision arrives before the boundary
- **WHEN** a provider-final revision arrives before the stale presentation boundary
- **THEN** the UI SHALL present the segment as confirmed and SHALL NOT show recognition incomplete

### Requirement: Realtime stream recovery remains bounded
The live conversation UI SHALL allow a commercially reasonable initial snapshot window and SHALL apply bounded backoff after a fallback snapshot so one slow stream cannot create a reconnect storm.

#### Scenario: Initial stream snapshot is temporarily slow
- **WHEN** the realtime stream is connected but its first complete snapshot needs more than two seconds and no more than five seconds to arrive
- **THEN** the UI SHALL keep reading the stream and SHALL NOT abort an otherwise healthy subscription

#### Scenario: Fallback snapshot succeeds after a stream timeout
- **WHEN** a stream attempt times out and the authoritative HTTP fallback snapshot succeeds
- **THEN** the UI SHALL render the recovered state and SHALL preserve increasing reconnect backoff until a stream snapshot succeeds

### Requirement: Commercial release and privacy-safe verification
The release SHALL increment the desktop companion patch version and SHALL verify latency and recovery using metadata-only diagnostics that exclude audio, transcript content, and secrets.

#### Scenario: Release artifacts are published
- **WHEN** the optimized companion is promoted to production
- **THEN** macOS and Windows manifests SHALL identify version 1.1.5 and immutable checksums for the verified artifacts

#### Scenario: Production verification is recorded
- **WHEN** production deployment completes
- **THEN** the release record SHALL include health, terminal latency, watchdog state, and rollback identifiers without raw audio, transcript text, or complete credentials
