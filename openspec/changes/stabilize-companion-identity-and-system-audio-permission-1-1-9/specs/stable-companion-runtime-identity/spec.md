## ADDED Requirements

### Requirement: Companion runtime identity is stable across launch methods
The companion SHALL select the same product-owned user-data directory before Electron sessions and local stores initialize, regardless of localized product name or whether the packaged app is launched from Finder, `open`, or its executable.

#### Scenario: Packaged app restarts normally
- **WHEN** the same installed companion is relaunched without a `--user-data-dir` argument
- **THEN** it SHALL load the same device pairing identity and settings used by the prior stable launch

#### Scenario: Stable identity already exists
- **WHEN** both the stable directory and a legacy product-name directory contain pairing identities
- **THEN** the stable identity SHALL win and SHALL NOT be overwritten or blended with the legacy identity

### Requirement: Legacy local state migration is minimal and safe
The companion SHALL migrate only allowlisted pairing credential and user-setting files from the previous product-name directory when their stable counterparts are absent.

#### Scenario: First 1.1.9 launch after an older installation
- **WHEN** the stable directory has no pairing identity and the legacy directory contains a valid pairing identity
- **THEN** the companion SHALL preserve that identity in the stable directory before device registration begins

#### Scenario: Volatile or sensitive artifacts exist in the legacy directory
- **WHEN** the legacy directory contains Chromium caches, diagnostics, screenshots, transcripts, or media artifacts
- **THEN** the migration SHALL NOT copy those artifacts into the stable directory

### Requirement: System-audio permission failure is explicit and contained
On macOS, the companion SHALL treat a non-granted Screen & System Audio Recording permission as a system-channel degradation, SHALL NOT repeatedly acquire display sources while denied, and SHALL NOT emit an unhandled promise rejection.

#### Scenario: Interview starts while screen permission is denied
- **WHEN** microphone permission is available but macOS screen permission is not granted
- **THEN** microphone capture SHALL remain eligible to publish and system audio SHALL report an actionable permission-required state

#### Scenario: Display-source acquisition rejects
- **WHEN** Electron rejects display-source acquisition despite a prior permission check
- **THEN** the main process SHALL contain the rejection, return an unavailable capture result, and keep the app process alive

#### Scenario: User grants permission
- **WHEN** the user enables Screen & System Audio Recording and restarts the companion
- **THEN** the companion SHALL re-evaluate permission and allow the existing system-audio recovery path to start capture

### Requirement: Companion 1.1.9 is independently verifiable
The release SHALL identify version 1.1.9 and preserve a separate 1.1.8 rollback artifact.

#### Scenario: Local 1.1.9 acceptance build starts
- **WHEN** the verified 1.1.9 package is installed locally
- **THEN** it SHALL use the stable identity directory, expose permission-specific diagnostics, and start without replacing the retained 1.1.8 rollback package
