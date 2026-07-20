## ADDED Requirements

### Requirement: End-to-end trace correlation
The system SHALL correlate capture, transport, ASR, event publication, and web rendering with privacy-safe trace and segment identifiers.

#### Scenario: A transcript is delayed
- **WHEN** an operator inspects a delayed synthetic transcript
- **THEN** diagnostics identify capture-to-send, ingress, queue, ASR first-token, finalization, event push, and web-render timing without exposing raw audio

### Requirement: Resource and queue telemetry
The system SHALL report active connections, file descriptors, queue duration, dropped frames, reconnect attempts, provider sessions, event lag, and duplicate suppression per service and channel.

#### Scenario: Queue approaches its limit
- **WHEN** ingress or provider queue duration reaches its warning threshold
- **THEN** metrics and structured logs expose the session-safe identifier, channel, depth, duration, and shedding action

### Requirement: Privacy-safe diagnostics
Operational logs and generated diagnostic reports SHALL exclude raw audio payloads, secrets, access tokens, and transcript text by default.

#### Scenario: Support report is generated
- **WHEN** a user or operator exports a realtime diagnostic report
- **THEN** it contains states, counts, timings, versions, device classes, and error codes but no raw audio or transcript content

### Requirement: Commercial release SLO gates
The new realtime path SHALL pass defined latency, reconnect, soak, and resource acceptance gates before legacy transport is removed.

#### Scenario: Normal reference run
- **WHEN** synthetic two-channel speech runs under the supported reference network
- **THEN** speech-to-web final transcript latency is p95 at or below two seconds and control API latency is p95 at or below 500 ms

#### Scenario: Thirty-minute soak
- **WHEN** a two-channel interview runs for thirty minutes with periodic speech and reconnect events
- **THEN** connection count, file descriptors, memory, queue duration, and provider session count remain bounded with no unbounded growth

#### Scenario: Five-second interruption
- **WHEN** network access is unavailable for five seconds and then returns
- **THEN** desktop and web consumers recover within five seconds after connectivity returns and report any unrecoverable audio gap explicitly
