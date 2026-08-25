## ADDED Requirements

### Requirement: Unified Release 1.1 desktop baseline

The product SHALL publish version 1.1.0 artifacts for macOS Apple Silicon, macOS Intel, and Windows x64 under the existing desktop application identity and backend protocol.

#### Scenario: Supported desktop downloads expose Release 1.1

- **WHEN** a user opens the production desktop download page after deployment
- **THEN** all three supported platform entries report version 1.1.0
- **AND** each entry resolves to the artifact whose size and SHA-256 match the release manifest

### Requirement: macOS production integrity

Both macOS Release 1.1 artifacts SHALL retain Bundle Identifier `com.offersteady.companion` and pass the existing Developer ID, Hardened Runtime, notarization, stapling, codesign, Gatekeeper, and stapler validation gates.

#### Scenario: macOS artifact validation succeeds

- **WHEN** either the arm64 or x64 Release 1.1 DMG artifact is prepared for publication
- **THEN** publication is blocked unless its production metadata records verified signing, notarization, and a non-development build

### Requirement: Honest Windows release status

The Windows x64 Release 1.1 installer SHALL expose its actual signing state and SHALL NOT be described as Authenticode verified when no verified signing certificate was used.

#### Scenario: Unsigned Windows package is published

- **WHEN** the Windows installer has no verified Authenticode signature
- **THEN** its manifest metadata retains the non-verified signing state
- **AND** its installer structure and checksum still pass the repository release validation
