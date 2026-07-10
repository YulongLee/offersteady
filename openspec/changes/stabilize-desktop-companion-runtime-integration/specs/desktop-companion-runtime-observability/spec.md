## ADDED Requirements

### Requirement: Companion runtime status MUST be stage-based
The system SHALL represent desktop companion runtime state as explicit stages instead of a single connected/not-connected flag.

#### Scenario: Device is registered but no interview is bound
- **WHEN** the desktop companion has registered its machine code with the backend but no Web interview has bound that code
- **THEN** backend runtime status reports `deviceRegistered=true`, `machineCodeBound=false`, and the companion displays an unbound state

#### Scenario: Interview is bound but not live
- **WHEN** the Web app binds a machine code during interview preparation before starting the live interview
- **THEN** backend runtime status reports the bound session and `sessionLive=false`, and the companion does not start publishing audio frames

#### Scenario: Interview is live
- **WHEN** the Web app starts the bound interview session
- **THEN** backend runtime status reports `sessionLive=true` and the companion may create publishers for available sources

### Requirement: Runtime status MUST expose actionable failure reasons
The system SHALL include machine-readable failure reason codes and user-readable guidance for desktop, backend, transport, media, ASR and Web consumption failures.

#### Scenario: Desktop uses a different backend URL than Web
- **WHEN** the companion registers against a backend origin that is different from the Web app's configured API origin
- **THEN** the diagnostic status reports `backend-mismatch` and shows both origins without exposing secrets

#### Scenario: WebSocket publisher fails
- **WHEN** the companion cannot create or connect a realtime publisher
- **THEN** runtime status identifies whether the failure occurred at token creation, WebSocket connection, authorization, expiry, or frame acknowledgement

### Requirement: Diagnostic reports MUST avoid sensitive payloads
The system MUST generate desktop integration diagnostic reports without storing raw audio bytes, screen images, screenshots, API keys, publisher tokens, refresh tokens, or full sensitive transcripts.

#### Scenario: User exports diagnostics
- **WHEN** a diagnostic report is generated after a failed companion session
- **THEN** it includes timestamps, stage states, device labels, model/provider names, frame counters, error codes and redacted URLs, but excludes raw media and credentials

### Requirement: Status lights MUST reflect verified runtime stages
The companion SHALL only show a source or connection as successful when the corresponding backend or media stage has been verified.

#### Scenario: Permission exists but no audio signal is detected
- **WHEN** a source has permission and a live track but no audio signal above the diagnostic threshold
- **THEN** the source status remains warning or silent rather than showing a successful capture state

#### Scenario: Frames are generated but ASR fails
- **WHEN** the companion publishes audio frames and the backend ASR returns an error
- **THEN** the source status indicates publishing succeeded while transcription failed
