## ADDED Requirements

### Requirement: Companion MUST block ready state until capture validation passes
The companion SHALL not display itself as ready for interview capture until microphone, computer output and screen validation have each produced real runtime evidence.

#### Scenario: Microphone has no signal
- **WHEN** microphone permission exists but no signal or PCM frame is produced during validation
- **THEN** the companion reports microphone validation failed and does not mark the overall assistant as ready

#### Scenario: Computer output has no signal
- **WHEN** computer output capture opens but no playback signal or PCM frame is produced during validation
- **THEN** the companion reports interviewer-audio validation failed and does not mark the overall assistant as ready

#### Scenario: Screen preview has no frame
- **WHEN** screen capture permission exists but no display frame is produced
- **THEN** the companion reports screen validation failed and does not mark screen capture as ready

### Requirement: Validation failures MUST be actionable
The companion SHALL show a precise reason code and recovery instruction for every failed validation stage.

#### Scenario: Native helper is missing
- **WHEN** the packaged app does not include or cannot launch the macOS capture runtime
- **THEN** the companion reports `native-runtime-missing` and instructs the user to reinstall or rebuild the companion

#### Scenario: Unsupported macOS version
- **WHEN** the current macOS version cannot support the selected native capture path
- **THEN** the companion reports `unsupported-macos-version` and does not claim audio/video monitoring support
