## ADDED Requirements

### Requirement: Healthy companion states use one green presentation
The desktop companion SHALL present registered idle, active interview, silent audio, and transient automatic recovery states with the same green healthy visual language, without requiring an active interview binding.

#### Scenario: Registered device waiting for an interview
- **WHEN** the companion is registered and the service is reachable but no interview is currently bound
- **THEN** the companion displays a green healthy indicator instead of a red failure indicator

#### Scenario: Active interview
- **WHEN** the companion is connected to an active interview and capture is operating
- **THEN** the companion continues to display the same green healthy indicator

#### Scenario: Transient automatic recovery
- **WHEN** a recoverable transport interruption is being retried automatically and no terminal failure has been confirmed
- **THEN** the companion keeps the user-facing indicator green

### Requirement: Silence is not presented as a device fault
The desktop companion SHALL distinguish an available audio channel with no current signal from a permission or device failure.

#### Scenario: Available channel is silent
- **WHEN** an audio channel is open and available but its current measured level is zero
- **THEN** its status indicator remains green and its meter remains at the real zero level

#### Scenario: Audio signal arrives
- **WHEN** the available channel receives a real audio signal
- **THEN** the meter reflects the measured signal without changing the healthy color semantics

### Requirement: Confirmed actionable faults use red presentation
The desktop companion SHALL display red only for confirmed conditions that require user action or cannot be recovered automatically, including service registration failure, permission denial, unsupported capture, and unavailable devices.

#### Scenario: Permission denied
- **WHEN** the operating system denies a required capture permission
- **THEN** the affected status indicator displays red with an actionable explanation

#### Scenario: Device unavailable
- **WHEN** a required capture source is confirmed unavailable or unsupported
- **THEN** the affected status indicator displays red

#### Scenario: Service registration fails
- **WHEN** the companion cannot register or reach its configured service after the existing failure handling marks the runtime as an error
- **THEN** the connection indicator displays red

### Requirement: Health presentation does not change the realtime pipeline
The implementation MUST leave audio capture, audio transport, ASR, transcript delivery, screenshot capture, and interview binding protocols unchanged.

#### Scenario: Health UI update is applied
- **WHEN** the new health presentation is enabled
- **THEN** the realtime pipeline uses the same capture and transport configuration as before the update

### Requirement: Version 1.2.12 is distributed consistently
The production desktop download manifest SHALL expose version 1.2.12 for macOS Apple Silicon, macOS Intel, and Windows x64 after their platform-specific verification succeeds.

#### Scenario: Production publication succeeds
- **WHEN** all three versioned artifacts pass their required verification and upload completes
- **THEN** the production manifest exposes all three targets at version 1.2.12 without changing unrelated production services or user data

#### Scenario: Production publication cannot be verified
- **WHEN** a required artifact, signature, notarization, checksum, upload, or health check fails
- **THEN** the release stops before presenting an unverified target as the current production download
