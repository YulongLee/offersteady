## ADDED Requirements

### Requirement: Only verified macOS DMGs are production-publishable
The publication workflow SHALL reject a macOS production artifact unless it is a DMG whose Developer ID signature, architecture, Gatekeeper assessment, notarization ticket, checksum, and metadata have been verified.

#### Scenario: Development ZIP is passed to production publication
- **WHEN** an operator attempts to publish a macOS ZIP or metadata marked `local-development` to the production channel
- **THEN** the command fails before mutating OSS or the website release manifest

#### Scenario: Verified DMG is prepared for publication
- **WHEN** a production DMG passes codesign, architecture, Gatekeeper, and stapler validation
- **THEN** metadata records `signingStatus: verified`, `notarized: true`, the actual checksum and size, and the DMG filename

### Requirement: Website manifest exposes verified DMGs per architecture
The website release manifest SHALL expose separate arm64 and x64 macOS DMGs while preserving the stable bundle identity and unrelated platform entries.

#### Scenario: Both Mac architectures are published
- **WHEN** verified arm64 and x64 DMGs are uploaded successfully and the manifest is deployed
- **THEN** Apple Silicon users receive the arm64 DMG, Intel users receive the x64 DMG, and the Windows entry remains unchanged

### Requirement: Publication remains fail-safe
The workflow SHALL keep the current live manifest unchanged until every requested production artifact has uploaded and the updated manifest has passed regression validation.

#### Scenario: One architecture upload fails
- **WHEN** OSS upload or validation fails for either requested Mac architecture
- **THEN** deployment stops and the existing live download entries remain active

### Requirement: Public download integrity is verifiable
Each published macOS entry SHALL provide a versioned OSS object, file size, and SHA-256 checksum matching the final notarized DMG.

#### Scenario: Public artifact is downloaded
- **WHEN** the website download endpoint redirects to the published macOS object
- **THEN** the downloaded bytes match the manifest size and SHA-256 checksum
