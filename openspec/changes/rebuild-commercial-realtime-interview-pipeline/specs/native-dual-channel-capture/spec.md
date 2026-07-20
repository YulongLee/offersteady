## ADDED Requirements

### Requirement: Single native capture ownership
The desktop companion SHALL run at most one native capture supervisor per active interview, and that supervisor SHALL exclusively own microphone and system-output capture while the production native path is active.

#### Scenario: Active interview starts capture
- **WHEN** a paired desktop receives a valid start command for an interview
- **THEN** exactly one native supervisor starts and no Electron main-process or renderer fallback opens a duplicate audio source

#### Scenario: Duplicate start command arrives
- **WHEN** the supervisor receives a repeated start command for the same active session
- **THEN** it returns the existing capture state without creating another capture process or publisher

### Requirement: Independent role channels
The native supervisor SHALL emit microphone audio as `candidate` input and system-output audio as `interviewer` input using independent source health and sequence state.

#### Scenario: Both sources are available
- **WHEN** microphone and system-output capture are authorized and active
- **THEN** the supervisor emits separately labelled channel frames without mixing their samples

#### Scenario: One source fails
- **WHEN** one channel becomes unavailable while the other remains healthy
- **THEN** the healthy channel continues and the failed channel reports a channel-scoped degraded state

### Requirement: Device and permission recovery
The supervisor SHALL observe default input changes, device removal, and permission state, and SHALL recover a channel without replacing the stable desktop device identity.

#### Scenario: AirPods connect during an interview
- **WHEN** AirPods become the default microphone after capture has started
- **THEN** the microphone channel reconfigures to the new valid format and resumes without machine-code rebinding

#### Scenario: Permission is denied
- **WHEN** macOS denies microphone or system-audio permission
- **THEN** the affected channel emits a specific permission-required state and does not produce synthetic or silent placeholder audio

### Requirement: Ephemeral bounded audio handling
The desktop SHALL keep raw audio only in memory and SHALL limit buffered audio to two seconds per channel.

#### Scenario: Network remains unavailable
- **WHEN** transport cannot acknowledge audio for longer than the buffer duration
- **THEN** the desktop drops the oldest non-final audio, reports a gap metric, and does not write raw audio to disk
