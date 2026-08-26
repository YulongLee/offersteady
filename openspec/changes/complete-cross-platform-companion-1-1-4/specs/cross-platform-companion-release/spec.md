## ADDED Requirements

### Requirement: Supported desktop platforms share one release version
The production companion manifest SHALL publish macOS Apple Silicon, macOS Intel and Windows x64 artifacts from the same approved patch release, and each artifact MUST contain the advertised version and realtime protocol version.

#### Scenario: Cross-platform 1.1.4 release is published
- **WHEN** the companion recovery correction is made publicly downloadable
- **THEN** all three supported target entries advertise version 1.1.4 and protocol 2.0
- **AND** no supported target remains on 1.1.2 or 1.1.3

### Requirement: Desktop branding uses the approved authoritative icon
The packaged macOS applications, Windows executable/installer and in-window companion brand mark SHALL derive from the approved current brand icon and MUST NOT silently fall back to a stale desktop-only asset.

#### Scenario: Release packages are built
- **WHEN** macOS or Windows production artifacts are generated
- **THEN** automated verification proves the packaging inputs match the approved brand asset
- **AND** the renderer displays the matching icon family

### Requirement: Published artifacts remain immutable by version
The release workflow MUST issue a new patch version whenever published companion bytes change and SHALL upload each artifact under a versioned object key with matching size and SHA-256 metadata.

#### Scenario: Correcting an already-published package
- **WHEN** a branding or platform-coverage defect is found after 1.1.3 publication
- **THEN** corrected artifacts are released as 1.1.4 instead of overwriting 1.1.3

### Requirement: Platform signing status is truthful
The production release manifest SHALL accurately report the signing and notarization state of each artifact and MUST NOT represent an unsigned Windows installer as verified.

#### Scenario: Mixed platform security capabilities
- **WHEN** notarized macOS artifacts and an unsigned Windows installer are published together
- **THEN** macOS entries report verified and notarized
- **AND** the Windows entry reports local-development and not notarized

### Requirement: Production manifest update is cross-platform atomic
The release workflow SHALL require all supported 1.1.4 artifacts to upload successfully before writing the production manifest that exposes them.

#### Scenario: One artifact cannot be prepared or uploaded
- **WHEN** any macOS or Windows target fails validation or upload
- **THEN** the production manifest is not updated to a mixed 1.1.4 release

#### Scenario: All artifacts pass
- **WHEN** all three 1.1.4 artifacts pass their platform-appropriate checks and uploads
- **THEN** one manifest generation replaces all three supported target entries
