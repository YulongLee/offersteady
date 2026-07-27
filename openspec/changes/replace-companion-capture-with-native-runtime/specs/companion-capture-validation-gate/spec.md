## ADDED Requirements

### Requirement: Companion MUST block ready state until capture validation passes
The companion SHALL not display itself as ready for interview capture until microphone, computer output and screen validation have each produced real runtime evidence.

#### Scenario: Microphone has no signal
- **WHEN** microphone permission exists but no signal or PCM frame is produced during validation
- **THEN** the companion reports microphone validation failed and does not mark the overall assistant as ready

#### Scenario: Computer output has no signal
- **WHEN** computer output capture opens but no playback signal or PCM frame is produced during validation
- **THEN** the companion reports interviewer-audio validation failed and does not mark the overall assistant as ready

#### Scenario: Assistant is idle before realtime publishing starts
- **WHEN** the assistant is open and no realtime publisher has taken over the audio sources
- **THEN** the local monitor actively samples microphone and computer-output loopback levels regardless of whether the optional native helper executable is present

#### Scenario: Screen preview has no frame
- **WHEN** screen capture permission exists but no display frame is produced
- **THEN** the companion reports screen validation failed and does not mark screen capture as ready

#### Scenario: Audio level changes rapidly
- **WHEN** raw microphone or computer-output levels vary between adjacent samples
- **THEN** the companion applies bounded decibel mapping and attack/release smoothing to the displayed meter without changing the raw capture data

#### Scenario: Companion opens at its default size
- **WHEN** the desktop companion opens with all standard controls visible
- **THEN** the window fits the controls without leaving a large unused area below the footer and remains vertically scrollable when resized smaller

#### Scenario: Native helper does not inherit system-audio permission
- **WHEN** macOS rejects the separately signed native helper while the parent companion is authorized
- **THEN** the companion captures computer output through Electron's parent-app CoreAudio Tap path instead of exposing a connected but silent fallback track

#### Scenario: System-audio source lookup fails
- **WHEN** macOS rejects or cannot enumerate a desktop source for system audio
- **THEN** the companion performs one capture request, backs off repeated source lookup failures, and keeps microphone capture and publishing active

#### Scenario: Local ad-hoc macOS build captures computer output
- **WHEN** a local build has Screen & System Audio Recording permission but cannot retain a separate Audio Capture grant across rebuilds
- **THEN** the companion uses Electron's ScreenCaptureKit permission path and does not require a second web-page permission request

### Requirement: Validation failures MUST be actionable
The companion SHALL show a precise reason code and recovery instruction for every failed validation stage.

#### Scenario: Native helper is missing
- **WHEN** the packaged app does not include or cannot launch the macOS capture runtime
- **THEN** the companion reports `native-runtime-missing` and instructs the user to reinstall or rebuild the companion

#### Scenario: Unsupported macOS version
- **WHEN** the current macOS version cannot support the selected native capture path
- **THEN** the companion reports `unsupported-macos-version` and does not claim audio/video monitoring support
