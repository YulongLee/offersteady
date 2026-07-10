## ADDED Requirements

### Requirement: The system MUST provide one unified realtime speech service
The system SHALL provide one unified Realtime Speech Service that accepts authorized live audio input, binds it to one Interview Session, and orchestrates transcript generation, question detection, AI answer triggering, and session-scoped storage.

#### Scenario: Realtime speech starts for an active interview session
- **WHEN** an authorized capture client starts streaming live audio for an active interview session
- **THEN** the system MUST route the stream through one realtime speech entrypoint instead of requiring the client to separately coordinate ASR, question detection, chat triggering, and storage

#### Scenario: Realtime speech remains scoped to live interview assistance
- **WHEN** the service processes a live audio stream
- **THEN** it MUST own transcript generation, subtitle updates, question detection, chat orchestration, answer streaming, and session-scoped recording for that stream

### Requirement: The realtime speech service MUST bind authorized audio streams to interview sessions
The system SHALL require session-bound authorization for realtime audio publishing and MUST reject audio streams that are not explicitly bound to the current interview session, user, and permitted capture source.

#### Scenario: Authorized audio publisher connects
- **WHEN** a capture client presents a valid session-bound authorization to the realtime speech service
- **THEN** the system MUST accept the realtime connection and associate incoming audio with the referenced interview session

#### Scenario: Unauthorized or expired audio publisher connects
- **WHEN** a capture client presents an invalid, expired, revoked, or mismatched authorization
- **THEN** the system MUST reject the connection and MUST NOT expose session-sensitive transcript or answer data

### Requirement: The realtime speech service MUST support low-latency streaming audio transport
The system SHALL support a low-latency streaming transport for realtime audio and transcript events so the approved prototype can show near-live subtitles and answer progress without changing page structure.

#### Scenario: Realtime audio frames arrive normally
- **WHEN** the service receives ordered audio frames over an active realtime connection
- **THEN** it MUST preserve source identity, time ordering, and session association before passing the frames into the ASR pipeline

#### Scenario: Realtime connection is interrupted
- **WHEN** the transport is interrupted or reconnects within policy
- **THEN** the system MUST expose a reconnect or degraded state and MUST NOT pretend uninterrupted realtime coverage when audio continuity cannot be guaranteed

### Requirement: The realtime speech service MUST isolate ASR behind a replaceable gateway
The system SHALL isolate realtime transcription behind a provider-agnostic ASR gateway so the product can use Qwen Realtime ASR first while retaining the ability to switch realtime speech providers later.

#### Scenario: Default realtime ASR provider uses Qwen
- **WHEN** the first production-capable realtime speech provider is configured
- **THEN** the realtime speech service MUST be able to call Qwen Realtime ASR through the ASR gateway boundary

#### Scenario: Realtime ASR provider changes later
- **WHEN** deployment switches to another provider with a compatible realtime transcription adapter
- **THEN** the realtime speech orchestration and public realtime speech contract MUST remain stable while the provider adapter changes behind the gateway

### Requirement: The realtime speech service MUST emit revision-aware realtime subtitles
The system SHALL emit revision-aware transcript and subtitle events so the live conversation area can display only the current text for each segment while preserving finality, overlap, and confidence state.

#### Scenario: Interim transcript is revised
- **WHEN** the ASR provider revises a transcript segment before final confirmation
- **THEN** the system MUST update the existing segment revision instead of creating a duplicate visible subtitle row

#### Scenario: Final transcript becomes available
- **WHEN** a transcript segment reaches final confirmation
- **THEN** the system MUST mark it as final and make it available to downstream question detection and session-scoped history

### Requirement: The realtime speech service MUST detect answerable interviewer questions safely
The system SHALL run question detection on authorized interview-session transcripts and MUST only trigger automatic answers for sufficiently complete interviewer questions while preserving manual confirmation or manual input for uncertain cases.

#### Scenario: Complete interviewer question is detected
- **WHEN** the service receives a sufficiently complete, final interviewer transcript segment or assembled question span
- **THEN** it MUST create one confirmed question event and invoke Chat Service at most once for that question version

#### Scenario: Transcript is uncertain or incomplete
- **WHEN** transcript confidence, overlap, source quality, or boundary confidence is below the answer threshold
- **THEN** the system MUST preserve a question-candidate or degraded state and MUST NOT auto-trigger a confirmed answer

### Requirement: The realtime speech service MUST invoke Chat Service through a decoupled orchestration boundary
The system SHALL invoke Chat Service through a decoupled orchestration layer so realtime speech can reuse session context, retrieval grounding, prompt policy, and answer streaming without embedding Chat logic into the ASR layer.

#### Scenario: Realtime question becomes answerable
- **WHEN** a confirmed question event is produced from realtime speech
- **THEN** the service MUST call Chat Service with the active interview session and allow Resume, JD, and Knowledge retrieval enhancement to apply through existing boundaries

#### Scenario: Chat Service is unavailable
- **WHEN** the realtime speech service cannot obtain an answer from Chat Service
- **THEN** it MUST preserve the transcript and confirmed question state while returning a terminal answer failure state rather than discarding the question

### Requirement: The realtime speech service MUST persist conversation records at session scope
The system SHALL persist finalized transcript segments, confirmed questions, answer-task references, and related operational metadata as session-scoped records so a session can be restored or reviewed later.

#### Scenario: Realtime speech session progresses normally
- **WHEN** live transcript segments and confirmed questions are produced during one interview session
- **THEN** the system MUST store them under the current Interview Session rather than as transient client-only state

#### Scenario: Service reconnects or client reloads
- **WHEN** the client reconnects to the same live interview session
- **THEN** the system MUST be able to return the latest session-scoped transcript and answer state without requiring the client to reconstruct prior events locally

### Requirement: The realtime speech service MUST record usage and minimize sensitive retention
The system SHALL record structured usage and operational metadata for realtime speech tasks while minimizing retention of raw audio and excluding full audio payloads, provider secrets, and unnecessary sensitive transcript content from ordinary logs.

#### Scenario: Provider returns usage or timing metadata
- **WHEN** the realtime ASR or downstream answer generation pipeline reports usage, duration, or provider metadata
- **THEN** the system MUST attribute it to the related interview session and service task boundaries

#### Scenario: Realtime speech logs are emitted
- **WHEN** structured logs are recorded for realtime speech events
- **THEN** they MUST include request or connection metadata, session id, provider, state, latency, and error code, but MUST NOT include raw audio bytes or provider secrets in ordinary logs

### Requirement: The realtime speech service MUST degrade safely without breaking the approved prototype flow
The system SHALL degrade to subtitle-only, question-confirmation, or manual-input modes when realtime capture, ASR, or question detection becomes unavailable, while preserving the approved prototype interaction model.

#### Scenario: Realtime ASR is degraded
- **WHEN** the speech provider is slow, unavailable, or returns low-quality results
- **THEN** the system MUST expose a degraded state and keep manual question entry available instead of claiming reliable automatic interview assistance

#### Scenario: Capture source cannot be trusted
- **WHEN** the service cannot safely distinguish or trust the expected capture source within policy
- **THEN** it MUST suspend automatic answer triggering while preserving the rest of the live workspace flow
