## ADDED Requirements

### Requirement: Windows support claim requires release readiness
The system SHALL expose “Windows 已支持” only when an authorized readiness record confirms a signed Windows x64 artifact, compatible protocol, installation lifecycle, account/pairing flow, microphone capture and required physical-device verification. Ordinary marketing configuration MUST NOT override a failed readiness gate.

#### Scenario: All Windows readiness checks pass
- **WHEN** the current Windows x64 release satisfies every required gate
- **THEN** the homepage, download center and user guide consistently display Windows as supported

#### Scenario: Windows signing or core flow is incomplete
- **WHEN** any mandatory readiness check is pending, failed or expired
- **THEN** the product does not label Windows signing or complete readiness as verified
- **AND** any separately operator-published download follows the explicit evidence wording and withdrawal rules below

### Requirement: Supported Windows scope is explicit
The support statement SHALL include minimum Windows version, x64 architecture and actual microphone/system-audio capabilities. If a limited Windows mode is approved, every support claim MUST disclose the limitation and recovery inputs.

#### Scenario: Windows system audio is unavailable in an approved limited release
- **WHEN** the user views Windows support information
- **THEN** the page clearly identifies unavailable system audio and available microphone, manual and screenshot paths

### Requirement: Windows support evidence expires with the release
Readiness SHALL be version-specific and SHALL be revoked when the artifact is withdrawn, the protocol becomes incompatible or a critical capability regression is confirmed.

#### Scenario: Supported Windows release is withdrawn
- **WHEN** release management withdraws the current supported artifact
- **THEN** new visitors no longer see the withdrawn version as supported or downloadable

### Requirement: Operator publication is distinct from signing evidence
The release manifest SHALL represent the operator's distribution decision separately from code-signing and macOS notarization evidence. An artifact explicitly marked `published` by the authorized operator MAY be offered from the product download center when its object key, file size and SHA-256 are present, even if signing evidence remains `local-development` or pending. The UI MUST describe it as a downloadable formal product release and MUST NOT falsely label signing or notarization as verified. Internal, failed or withdrawn artifacts MUST remain inaccessible.

#### Scenario: Operator confirms the current companion artifacts as formal releases
- **WHEN** the current macOS Apple Silicon, macOS Intel and Windows x64 entries are marked `published` and their stored artifacts remain reachable
- **THEN** the download center exposes all three download actions
- **AND** the signing and notarization fields retain their factual values

#### Scenario: An unpublished artifact filename is requested directly
- **WHEN** the requested artifact is internal, failed or withdrawn
- **THEN** the backend returns not found and does not create a signed storage URL
