## ADDED Requirements

### Requirement: Preparation establishes privacy-safe realtime readiness
When a desktop is bound to a preparing interview, the system SHALL validate and keep usable local microphone and system-audio sources warm and SHALL schedule best-effort provider readiness without uploading, transcribing, persisting, or billing preparation audio.

#### Scenario: Bound preparation becomes ready
- **WHEN** a user binds an online companion to a preparing interview and grants the required local permissions
- **THEN** the companion reports both local sources ready and the backend schedules both provider channels without changing the session to live or charging realtime usage

#### Scenario: Preparation audio remains local
- **WHEN** a warmed source receives sound before the user starts the interview
- **THEN** no audio frame, transcript event, answer request, or realtime usage charge is produced

#### Scenario: Warm readiness expires safely
- **WHEN** preparation is cancelled, unbound, ended, or remains idle beyond the readiness lifetime
- **THEN** the system closes or refreshes warmed resources without publishing buffered preparation audio

### Requirement: Live start promotes warmed sources
The companion SHALL transfer ownership of each healthy preparation source to the live publisher without closing and reopening that source, while preserving independent fallback and recovery for unavailable sources.

#### Scenario: Both warmed sources are promoted
- **WHEN** the authoritative session status changes from preparing to live while both warmed streams are healthy
- **THEN** the publisher consumes those exact streams once, starts production processing, and sends only post-live audio

#### Scenario: One warmed source is stale
- **WHEN** one transferred stream is ended, muted, missing, or otherwise unusable at promotion
- **THEN** the publisher reopens only that source while the other source starts without waiting for the failed source recovery

#### Scenario: Start remains non-blocking
- **WHEN** provider warmup has not completed when the user starts the interview
- **THEN** live entry returns without waiting for the warmup timeout and the first real frame remains authoritative

### Requirement: Endpointing is source-aware and bounded
The realtime client SHALL use a faster commercial silence tail for system audio than for microphone audio, SHALL emit exactly one terminal per source generation, and SHALL preserve sentence continuity across short natural pauses.

#### Scenario: System speech ends cleanly
- **WHEN** meaningful system speech is followed by at least the configured adaptive system tail
- **THEN** the client emits a prioritized terminal frame measured from the last meaningful speech boundary

#### Scenario: Candidate makes a short thinking pause
- **WHEN** microphone speech pauses for less than the configured microphone tail and then resumes
- **THEN** the client keeps the same turn active rather than prematurely finalizing it

#### Scenario: Residual program noise continues
- **WHEN** system audio falls materially below the turn peak but low residual noise remains
- **THEN** the client terminates from the last meaningful speech boundary within the bounded recovery window

### Requirement: Provisional transcripts remain continuously visible
The Web application SHALL render the newest provisional text during speaking, tail, and committing states, and finalization or timeout events SHALL update only the matching segment generation without erasing confirmed or newer content.

#### Scenario: Provider final is delayed
- **WHEN** a segment has provisional text and provider finalization is pending
- **THEN** the provisional text remains visible with a non-blocking status until final or bounded incomplete resolution

#### Scenario: A newer turn starts before the prior final
- **WHEN** a new segment begins while an older segment is still committing
- **THEN** the new segment renders immediately and a late event for the old generation cannot replace it

#### Scenario: Finalization exceeds the bound
- **WHEN** no authoritative final arrives within the configured finalization watchdog
- **THEN** the active text remains visible, its waiting indicator ends with an incomplete state, and subsequent turns continue

### Requirement: Realtime latency is diagnosable without sensitive content
The system SHALL expose content-free timing evidence for preparation, live start, publication, acknowledgement, endpointing, provider finalization, and Web rendering while excluding raw audio and transcript text.

#### Scenario: Operator diagnoses slow first text
- **WHEN** runtime diagnostics are requested for an authorized live session
- **THEN** the response identifies the available start-stage timestamps and a dominant bottleneck without returning audio or transcript content

#### Scenario: Operator diagnoses slow completion
- **WHEN** a terminalized segment reaches a final or incomplete state
- **THEN** diagnostics expose last-meaningful-speech-to-terminal, terminal-to-provider-final, and final-to-visible-state durations when available

### Requirement: Companion 1.2.5 preserves the approved product surface
The local acceptance build SHALL report version 1.2.5 and preserve the 1.2.4 layout, transparent icon family, bundle identity, workspace action, production endpoint defaults, and protocol compatibility.

#### Scenario: Apple Silicon local acceptance package
- **WHEN** the macOS arm64 1.2.5 package is built and installed for local testing
- **THEN** version, architecture, signing truth, icon semantics, endpoint defaults, and launch state are verified without deploying Backend or Web changes
