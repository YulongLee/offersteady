## ADDED Requirements

### Requirement: Preparation verifies real local audio signal
The companion SHALL distinguish an opened source from a source that has produced fresh real-signal evidence, SHALL display microphone and computer-output check status during preparation, and SHALL keep preparation audio local, ephemeral, untranscribed, and unbilled.

#### Scenario: Both sources produce real signal
- **WHEN** the user speaks into the selected microphone and plays a spoken computer-output sample while both local processors are active
- **THEN** the companion marks each corresponding source as checked using content-free timestamps and levels without publishing an audio frame

#### Scenario: Track is open but silent
- **WHEN** a source track is live but no signal crosses its verification threshold
- **THEN** the companion reports that the track is open but sound has not been detected and provides actionable check guidance instead of claiming readiness

#### Scenario: Manual-only interview is selected
- **WHEN** the user chooses an input path that does not use audio capture
- **THEN** the system permits preparation and live entry without obtaining or validating microphone or computer-output permission

### Requirement: Audio readiness is fresh and invalidatable
Audio-assisted live entry SHALL require fresh readiness for every required source, and readiness SHALL expire or become invalid after a relevant source lifecycle failure.

#### Scenario: Fresh checks permit live entry
- **WHEN** all required sources have live callbacks and signal evidence within the readiness lifetime
- **THEN** the audio-assisted entry control is enabled and shows that sound checks passed

#### Scenario: Readiness expires
- **WHEN** the most recent signal evidence exceeds 120 seconds without refresh
- **THEN** the affected source becomes unchecked and the user is asked to test it again before audio-assisted entry

#### Scenario: Device route changes after checking
- **WHEN** a checked track ends, becomes muted, stalls, loses permission, or its output route changes
- **THEN** readiness is invalidated immediately and the system does not enter live mode using the stale green state

### Requirement: Verified sources continue into live capture
The companion SHALL transfer each fresh, healthy checked source into the live publisher once and SHALL independently reopen only a source that fails the transition recheck.

#### Scenario: Checked sources are promoted
- **WHEN** the authoritative session becomes live while both checked sources remain healthy
- **THEN** the publisher consumes those same media streams without device reopen and publishes only audio captured after live authorization

#### Scenario: One checked source becomes stale at transition
- **WHEN** the transition recheck fails for one source but the other remains valid
- **THEN** the valid source starts immediately and only the stale source enters bounded reopen or recovery

### Requirement: Quiet first speech is not indefinitely gated
The live publisher SHALL retain a bounded pre-speech window and SHALL prevent adaptive noise learning from indefinitely suppressing sustained low-volume system speech.

#### Scenario: Quiet spoken system audio begins
- **WHEN** sustained speech-like system energy remains above the verification floor but below the previous adaptive start threshold
- **THEN** the publisher starts a segment within a bounded interval and includes the retained pre-speech audio so the first words are not dropped

#### Scenario: True digital silence continues
- **WHEN** system samples remain below the verification floor
- **THEN** the publisher does not create repeated speech segments or upload unbounded silence

### Requirement: Companion 1.2.6 preserves the approved product surface
The Apple Silicon local acceptance build SHALL report version 1.2.6 and SHALL preserve the approved layout, transparent icon family, bundle identity, workspace action, production endpoint defaults, and protocol compatibility.

#### Scenario: Local acceptance package is installed
- **WHEN** the 1.2.6 macOS arm64 application is built and installed
- **THEN** version, architecture, signing truth, identity, icon semantics, endpoints, launch state, and recoverable 1.2.5 rollback are verified without claiming Backend/Web production deployment
