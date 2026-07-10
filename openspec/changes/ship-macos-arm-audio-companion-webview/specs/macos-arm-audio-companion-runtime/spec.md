## ADDED Requirements

### Requirement: macOS arm64 companion MUST run on the current development Mac
The desktop companion SHALL provide a macOS Apple Silicon development build that can be launched on the current development machine and reports its architecture, app version, protocol version, and local distribution status.

#### Scenario: Developer launches arm64 companion
- **WHEN** the macOS arm64 companion is launched on an Apple Silicon Mac
- **THEN** it starts without Rosetta, displays its local development version, and reports `platform=macos` and `architecture=arm64`

#### Scenario: Local build artifact is available
- **WHEN** the desktop build command completes for macOS arm64
- **THEN** the project exposes a local artifact path or download entry marked as development/local rather than verified public distribution

### Requirement: Companion MUST request and monitor audio permissions explicitly
The desktop companion MUST request microphone/headset and system-audio permissions before capture and SHALL display the permission state for each source independently.

#### Scenario: Permissions are granted
- **WHEN** the user grants microphone/headset and system-audio permissions
- **THEN** the companion marks both sources as usable and allows a pre-capture audio test

#### Scenario: Permission is denied
- **WHEN** the user denies or revokes either permission
- **THEN** the companion does not capture that source and shows recovery guidance without silently falling back to hidden capture

### Requirement: Companion MUST capture microphone and system audio as separate sources
The macOS companion SHALL capture local microphone/headset input and computer/system audio as separate source streams whenever the platform grants both sources.

#### Scenario: Dual source capture starts
- **WHEN** the user starts an interview with both sources ready
- **THEN** the companion produces separate ordered audio frames for the microphone/headset source and the system-audio source

#### Scenario: One source is unavailable
- **WHEN** either microphone/headset or system audio is unavailable
- **THEN** the companion reports the unavailable source and continues only with user-approved available fallback modes

### Requirement: Companion MUST show capture health and volume monitoring
The desktop companion SHALL show real-time capture health for each active source, including online state, current capture state, and visible level/meter diagnostics.

#### Scenario: Source receives signal
- **WHEN** a selected source has live audio signal during testing or capture
- **THEN** the companion updates that source's meter and labels it as receiving audio

#### Scenario: Source is silent
- **WHEN** a selected source remains silent beyond the diagnostic threshold
- **THEN** the companion shows a warning and does not claim that monitoring is successful

### Requirement: Companion MUST provide visible controls for start, pause, resume, and stop
The companion MUST only capture after explicit user action and MUST provide visible controls to pause, resume, stop, disconnect, and quit.

#### Scenario: User starts interview capture
- **WHEN** the user clicks “开始面试” after sources are ready
- **THEN** the companion enters capturing state and displays a persistent visible capture indicator

#### Scenario: User stops capture
- **WHEN** the user clicks stop, disconnects the device, or ends the interview
- **THEN** the companion stops capturing, stops sending frames, and clears transient audio buffers

### Requirement: Companion MUST NOT retain raw audio by default
The desktop companion MUST keep audio only in bounded transient memory buffers for live transport and MUST NOT write local recording files under the default policy.

#### Scenario: Session ends
- **WHEN** the user ends or disconnects from an interview session
- **THEN** the companion clears pending audio buffers and leaves no local recording file behind
