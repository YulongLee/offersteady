## ADDED Requirements

### Requirement: End-to-end trace correlation
The system SHALL correlate capture, transport, ASR, event publication, and web rendering with privacy-safe trace and segment identifiers.

#### Scenario: A transcript is delayed
- **WHEN** an operator inspects a delayed synthetic transcript
- **THEN** diagnostics identify capture-to-send, ingress, queue, ASR first-token, finalization, event push, and web-render timing without exposing raw audio

#### Scenario: Operator inspects a complete realtime trace
- **WHEN** one microphone or system-audio frame produces a partial or final transcript event
- **THEN** the same privacy-safe trace exposes T0 desktop capture, T1 desktop WebSocket send, T2 backend receive, T3 queue enter, T4 queue leave, T5 provider append, T6 provider partial receive, T7 provider final receive, T8 Redis event append, T9 SSE send, T10 browser receive, and T11 browser render timestamps where those stages apply
- **AND** the trace includes session-safe identifier, channel, sequence, utterance identifier, and event identifier without raw audio or transcript text

#### Scenario: Operator compares stage distributions
- **WHEN** completed traces are summarized for a reference run
- **THEN** diagnostics report count, p50, p95, p99, and maximum for desktop send, network, preprocessing, queue wait, ASR input lag, provider partial, Redis event append, SSE delivery, browser render, end-to-end partial, speech-end to commit, commit to final, and speech-end to final

#### Scenario: Operator isolates first-partial subtitle latency
- **WHEN** a real provider partial is delivered through Redis and SSE to the live React workspace
- **THEN** the trace distinguishes speech start, first desktop frame send, backend receive, provider append, provider partial receive, Redis XADD, Redis XREAD, SSE send, browser receive, browser state update, and React commit
- **AND** the summary reports count, p50, p95, p99, and maximum for every adjacent stage and speech-start to browser first-partial latency
- **AND** a run that uses an in-memory event fallback is rejected as realtime Redis evidence

### Requirement: Resource and queue telemetry
The system SHALL report active connections, file descriptors, queue duration, dropped frames, reconnect attempts, provider sessions, event lag, and duplicate suppression per service and channel.

#### Scenario: Queue approaches its limit
- **WHEN** ingress or provider queue duration reaches its warning threshold
- **THEN** metrics and structured logs expose the session-safe identifier, channel, depth, duration, and shedding action

#### Scenario: Producer and consumer rates diverge
- **WHEN** a channel receives audio faster than its ASR worker consumes it
- **THEN** telemetry reports per-channel frames in, frames out, queue depth, oldest frame age, queue wait, provider session recreation count, and provider append count so sustained backlog is distinguishable from provider latency

#### Scenario: Redis event consumer is inspected
- **WHEN** an operator inspects the transcript event stream during a reference run
- **THEN** diagnostics expose XADD and XREAD timestamps, consumer lag, stream length, read mode, and pending-message applicability without delaying event delivery

#### Scenario: Provider connection reuse is inspected
- **WHEN** an operator inspects a running interview by channel
- **THEN** diagnostics expose ASR connection create count, reconnect count, current and completed connection lifetime, finalized utterance count, and utterances per connection

#### Scenario: System first partial is inspected
- **WHEN** system audio opens a speech turn and later produces its first effective partial
- **THEN** diagnostics expose system VAD trigger, system speech start, system first effective partial, and frames before first partial without recording audio or transcript text

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
