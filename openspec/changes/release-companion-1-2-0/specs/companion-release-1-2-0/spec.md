## ADDED Requirements

### Requirement: Release identity is unambiguous
The companion release SHALL identify as version 1.2.0 in package metadata, application metadata, artifact names, and production manifest entries.

#### Scenario: User inspects an installed 1.2.0 companion
- **WHEN** the installed application reports its version and bundle identity
- **THEN** it SHALL report version 1.2.0 and the existing bundle identifier `com.offersteady.companion`

### Requirement: macOS production artifacts are trusted and architecture-correct
The release SHALL provide Apple Silicon and Intel macOS artifacts that pass Developer ID signing, Hardened Runtime, notarization, stapling, Gatekeeper, hash, and target-architecture verification.

#### Scenario: macOS artifact fails a production trust check
- **WHEN** either architecture fails signing, notarization, stapling, Gatekeeper, hash, or architecture validation
- **THEN** the production manifest SHALL NOT be updated to expose 1.2.0 macOS downloads

### Requirement: Windows trust status is truthful
The release SHALL package and structurally validate the Windows x64 installer and SHALL report its actual code-signing state without claiming verification when no trusted Windows certificate is available.

#### Scenario: Windows installer is unsigned
- **WHEN** the Windows x64 installer passes structural validation but has no trusted code signature
- **THEN** its release metadata SHALL identify it as unsigned or local-development and the website SHALL retain an explicit warning

### Requirement: Production publication is atomic and recoverable
The release SHALL upload immutable versioned artifacts before atomically updating the production manifest, SHALL preserve prior release artifacts, and SHALL maintain a Backend rollback point.

#### Scenario: Artifact upload or validation fails
- **WHEN** any required artifact fails upload, hash verification, or release validation
- **THEN** the existing production manifest SHALL remain active and no partial 1.2.0 release SHALL be advertised

#### Scenario: Production deployment succeeds
- **WHEN** all required artifacts and manifest entries are valid and the Backend deployment completes
- **THEN** public health, web state, manifest entries, and download URLs SHALL be verified before the release is declared complete

### Requirement: Release validation protects interview privacy
Release verification SHALL use synthetic fixtures and metadata-only health, signature, hash, and transport counters and SHALL NOT persist or publish raw interview audio, transcript text, screenshots, credentials, or personal information.

#### Scenario: Release evidence is recorded
- **WHEN** automated and physical acceptance results are documented
- **THEN** the evidence SHALL contain only non-content metadata and SHALL NOT include secrets or user interview content
