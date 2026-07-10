## ADDED Requirements

### Requirement: Windows support claim requires release readiness
The system SHALL expose “Windows 已支持” only when an authorized readiness record confirms a signed Windows x64 artifact, compatible protocol, installation lifecycle, account/pairing flow, microphone capture and required physical-device verification. Ordinary marketing configuration MUST NOT override a failed readiness gate.

#### Scenario: All Windows readiness checks pass
- **WHEN** the current Windows x64 release satisfies every required gate
- **THEN** the homepage, download center and user guide consistently display Windows as supported

#### Scenario: Windows signing or core flow is incomplete
- **WHEN** any mandatory readiness check is pending, failed or expired
- **THEN** the product does not label Windows as fully supported and does not expose an unverified download action

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

