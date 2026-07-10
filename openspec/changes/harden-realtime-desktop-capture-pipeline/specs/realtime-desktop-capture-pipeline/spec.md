## ADDED Requirements

### Requirement: Current session realtime capture SHALL be evidence-based
The system SHALL consider realtime conversation available only when the current live session has received at least one real desktop audio frame receipt or transcript for the active desktop binding.

#### Scenario: Bound device without frames remains waiting
- **WHEN** a desktop device is bound to a live interview session but the backend has no frame receipts and no transcripts for that session
- **THEN** the web interview page SHALL show a waiting/diagnostic state instead of implying realtime conversation is working

#### Scenario: Frame receipt marks source as active
- **WHEN** the backend receives a real microphone or system audio frame for the current session
- **THEN** the runtime status SHALL expose the source as active with frame count and last frame timestamp

### Requirement: ASR connectivity SHALL be tested separately from desktop capture
The system SHALL provide a synthetic PCM probe that verifies backend ingest and ASR without treating that probe as proof that the desktop capture path works.

#### Scenario: ASR probe accepted but desktop frames missing
- **WHEN** a synthetic PCM probe is accepted by the ASR pipeline but the current session has no real desktop frame receipts
- **THEN** diagnostics SHALL report ASR reachable and desktop capture blocked as separate results

### Requirement: Desktop capture SHALL support independent microphone and system degradation
The desktop companion SHALL publish microphone and computer-output health independently, and one failed source MUST NOT prevent the other source from publishing frames.

#### Scenario: Microphone works but system output fails
- **WHEN** microphone frames are published and system output capture is unavailable
- **THEN** the web page SHALL show single-channel realtime conversation and a system-output diagnostic warning

#### Scenario: Both sources fail
- **WHEN** neither microphone nor system output produces frames for the current live session
- **THEN** the web page SHALL show a blocking diagnostic state with the dominant bottleneck

### Requirement: macOS native capture SHALL be the primary realtime capture source
The macOS desktop companion SHALL use the native capture runtime as the primary source for microphone and system-output PCM frames, with Electron WebAudio only as fallback or local monitoring.

#### Scenario: Native microphone emits frames
- **WHEN** the native runtime receives microphone input during a live bound session
- **THEN** the desktop companion SHALL publish PCM frames to the backend and the backend SHALL record frame receipts

#### Scenario: Electron capture only has local meter
- **WHEN** Electron local monitoring detects volume but no backend frame receipts are produced
- **THEN** diagnostics SHALL report local signal without publish success rather than marking realtime conversation as working

### Requirement: Runtime startup path SHALL attempt native capture before WebAudio fallback
When the desktop app starts live publishing, it SHALL call native capture startup first and only use WebAudio capture when native is unavailable or fails to start.

#### Scenario: Native capture starts successfully
- **WHEN** native runtime starts successfully during a live start command
- **THEN** the publisher SHALL use native events as the active audio source and SHALL NOT initialize WebAudio capture as the primary path

#### Scenario: Native capture unavailable
- **WHEN** native startup fails or is unavailable
- **THEN** the publisher SHALL initialize WebAudio capture automatically so basic one or both audio channels can still attempt to publish

### Requirement: Web live conversation SHALL consume only current session transcripts
The web interview page SHALL display realtime conversation only from the current interview session and current user context.

#### Scenario: Historical transcripts exist for another session
- **WHEN** older sessions have transcripts for the same desktop device or machine code
- **THEN** the current live page SHALL NOT display those transcripts
