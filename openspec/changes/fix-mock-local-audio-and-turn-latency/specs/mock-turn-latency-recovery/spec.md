## ADDED Requirements

### Requirement: Previous round shutdown does not block next generation
On a valid answer submission the backend SHALL stop the interaction clock, invalidate the previous capture epoch and prevent its audio or transcript from entering a later round. The generating state and next generation SHALL proceed without waiting for an upstream close handshake. Detached cleanup SHALL be bounded and tracked until resource release.

#### Scenario: Old upstream close remains blocked
- **WHEN** a valid answer is submitted and the old ASR connection takes time to close
- **THEN** the generating state is published and the next generation starts while that close remains pending, with the old round fenced and no duplicate submission or extra waiting-time billing

#### Scenario: Late transcript arrives after submission
- **WHEN** an old upstream callback arrives after the round is fenced
- **THEN** it cannot change the next round's transcript or confirmed answer

#### Scenario: New round starts before old cleanup finishes
- **WHEN** a later round opens capture while the old connection closes
- **THEN** it uses isolated resources and old cleanup cannot close or unregister the new capture

### Requirement: Generation failures expose safe operational diagnostics
The backend SHALL record fixed stage names, duration and bounded error classifications for resume reading, provider waiting/request and output validation. It SHALL preserve current retry and provider-fault accounting, and SHALL not log source content, provider response bodies, exception text, secrets or device credentials.

#### Scenario: Provider fails or returns invalid output
- **WHEN** the provider request times out, returns an HTTP failure, or returns malformed/incomplete/repeated output
- **THEN** safe diagnostics distinguish the cause and the session retains its current retryable failure behavior without an implicit extra provider call

#### Scenario: Inputs contain sensitive markers
- **WHEN** a synthetic failure includes private markers in input or provider output
- **THEN** captured diagnostic logs contain none of those markers

### Requirement: Microphone disconnection cleanup is idempotent
The microphone endpoint SHALL release its own registration and tolerate an already disconnected socket without producing a secondary cleanup traceback.

#### Scenario: Peer has already disconnected
- **WHEN** endpoint cleanup closes an already disconnected microphone socket
- **THEN** cleanup completes without affecting a replacement connection or producing an unhandled WebSocketDisconnect
