## ADDED Requirements

### Requirement: Provider sessions prewarm concurrently
The Backend SHALL prepare at most one reusable ASR provider connection per active interview logical channel and SHALL allow microphone and system channel construction to run concurrently.

#### Scenario: Both channels are cold
- **WHEN** a live interview starts with no provider sessions
- **THEN** microphone and system prewarm SHALL run in parallel without opening duplicate connections for either channel

#### Scenario: A first frame races prewarm
- **WHEN** a first audio frame arrives while its channel prewarm is still opening
- **THEN** it SHALL join the same channel creation operation and SHALL NOT create a second provider connection

### Requirement: Live start has a bounded readiness gate
The Backend SHALL wait only for a configurable bounded interval for both prewarm operations before returning live-session start.

#### Scenario: Both provider sessions become ready
- **WHEN** both prewarms finish within the readiness deadline
- **THEN** live-session start SHALL return with both reusable connections ready for immediate audio

#### Scenario: Provider readiness times out
- **WHEN** one or both prewarms exceed the deadline or fail
- **THEN** live-session start SHALL continue through the existing lazy fallback and SHALL record the failure without exposing credentials or audio

### Requirement: First speech payload remains prompt and authentic
The Desktop SHALL send captured speech incrementally without waiting for utterance finalization, and the product SHALL display only provider-produced transcript text.

#### Scenario: Speech crosses the channel attack threshold
- **WHEN** recognizable speech remains above the adaptive threshold for the configured attack and minimum-speech window
- **THEN** the first payload SHALL include bounded pre-speech audio and SHALL be emitted before the normal 100 ms update cadence can add an extra full interval

#### Scenario: Provider has not produced text
- **WHEN** audio is flowing but the provider has not returned a non-empty partial
- **THEN** the UI SHALL retain a truthful recognition state and SHALL NOT invent placeholder transcript content

### Requirement: First-visible latency is measured once per utterance
The system SHALL record content-free timestamps for provider readiness, first audio append, first non-empty provider partial, first transcript event, and first browser paint, using only the earliest revision per session-channel-utterance.

#### Scenario: Later revisions arrive
- **WHEN** an utterance receives multiple provider partials and browser paints
- **THEN** later revisions SHALL NOT replace its first-partial or first-visible latency sample

#### Scenario: Production acceptance
- **WHEN** a live test supplies recognizable speech on both logical channels
- **THEN** queues SHALL remain bounded, no transcript content SHALL enter diagnostics, warm first-append p95 SHALL be below 250 ms, and speech-start-to-first-visible SHALL target p50 below 1.5 seconds and p95 below 3 seconds
