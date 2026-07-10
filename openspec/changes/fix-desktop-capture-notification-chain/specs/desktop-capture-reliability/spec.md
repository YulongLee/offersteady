## ADDED Requirements

### Requirement: Computer output capture reports only evidence-based readiness
The desktop companion SHALL distinguish selected computer output from working computer output. It MUST show active computer-output capture only when real signal is detected locally or when backend runtime reports published frames for the current live interview session.

#### Scenario: Local playback produces signal
- **WHEN** the user plays audio on the same computer while the companion is open
- **THEN** the computer-output meter moves from idle to receiving and reports a non-zero level

#### Scenario: Computer output is selected but silent
- **WHEN** the user has selected computer output but no local signal and no backend frame receipts exist
- **THEN** the companion shows a waiting/silent state rather than a successful connected state

#### Scenario: Computer output adapter cannot capture
- **WHEN** the platform adapter cannot access system output or required permissions/runtime are unavailable
- **THEN** the companion shows a concrete unsupported or permission error with the affected source kind

### Requirement: Realtime audio publishing is observable end to end
The system SHALL expose whether the current live interview session has received desktop audio frames and ASR/transcript results. The desktop and web surfaces MUST use current-session runtime, frame receipts, and transcript counts for diagnostics.

#### Scenario: Audio frame reaches backend
- **WHEN** the desktop companion publishes an audio frame for the current live session
- **THEN** backend runtime reports a frame receipt for the matching source kind and source id

#### Scenario: ASR fails after frame receipt
- **WHEN** backend receives an audio frame but ASR fails
- **THEN** runtime reports the frame as failed with a provider or ASR error instead of leaving it pending indefinitely

#### Scenario: Web receives transcript
- **WHEN** backend stores a current-session transcript from realtime speech
- **THEN** the web interview page displays the transcript in the live conversation area for that session

### Requirement: Screen capture validates real preview and capture
The desktop companion SHALL treat screen capture as ready only after it can obtain a real preview or capture result for the selected screen. Screenshot-answer requests MUST fail visibly when capture or upload fails.

#### Scenario: Screen preview succeeds
- **WHEN** the user clicks preview for a selected display
- **THEN** the companion shows an actual screen preview and marks screen capture ready

#### Scenario: Screen preview fails
- **WHEN** the companion cannot obtain a preview because of permission, runtime, or source errors
- **THEN** the companion shows a specific failure message and does not mark screen capture ready

#### Scenario: Web requests screenshot answer
- **WHEN** the web interview page requests a screenshot answer from the bound desktop
- **THEN** the desktop either uploads a real screenshot capture or reports a failed capture request with a user-readable reason

### Requirement: Interview entry notifies the user without flicker
The desktop companion SHALL show a stable connection-management message while unbound and a clear notification/status when a web interview binds the machine code and enters live capture. Polling MUST NOT cause the unbound connection copy to flicker or expose backend URLs.

#### Scenario: Companion is not bound
- **WHEN** no active interview session is bound to the companion
- **THEN** the connection card shows a stable instruction to open the interview home and enter the displayed connection code

#### Scenario: Interview binds desktop
- **WHEN** a web interview session binds the companion's machine code
- **THEN** the companion shows that the web interview is bound to this computer

#### Scenario: Interview enters live capture
- **WHEN** the bound interview session transitions to live
- **THEN** the companion surfaces a clear live-capture notification and starts publishing available audio sources

### Requirement: Full-chain diagnostic report uses non-sensitive evidence
The project SHALL provide a repeatable diagnostic/self-test path for desktop capture and realtime interview flow. The diagnostic output MUST include stage status, counters, timings, and error codes, and MUST NOT store raw audio, screenshots, transcripts, resumes, JD content, or knowledge material.

#### Scenario: Diagnostic identifies capture-layer failure
- **WHEN** local computer output or screen capture cannot produce evidence
- **THEN** the diagnostic report identifies capture or permission/runtime as the failing stage

#### Scenario: Diagnostic identifies backend or ASR failure
- **WHEN** frames reach backend but ASR/transcripts do not complete
- **THEN** the diagnostic report identifies backend receipt, ASR status, transcript count, and provider error codes

#### Scenario: Diagnostic passes full chain
- **WHEN** local capture, backend receipts, ASR transcript, web consumption, and screenshot capture all complete
- **THEN** the diagnostic report marks the full desktop interview chain as passed
