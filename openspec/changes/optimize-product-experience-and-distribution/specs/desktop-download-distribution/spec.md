## ADDED Requirements

### Requirement: Download center offers explicit supported platform and architecture choices
The download center SHALL render release-manifest entries for macOS Apple Silicon arm64, macOS Intel x64 and Windows x64 independently. It SHALL recommend a likely match from client signals while always allowing manual selection and correction.

#### Scenario: Apple Silicon user opens downloads
- **WHEN** client platform signals indicate macOS arm64 and a verified release exists
- **THEN** the page recommends “macOS Apple Silicon” and keeps Intel and Windows choices visible

#### Scenario: Platform detection is uncertain
- **WHEN** browser signals do not reliably identify platform or architecture
- **THEN** the page asks the user to select a package and provides instructions for checking their chip or Windows architecture

### Requirement: Only verified release artifacts are downloadable
A downloadable entry MUST include version, minimum OS, file size, SHA-256 checksum, publication time and successful signing status. macOS artifacts MUST be signed and notarized; Windows artifacts MUST be code-signed. Withdrawn or incomplete entries SHALL not expose an active download URL.

#### Scenario: Windows artifact is unsigned
- **WHEN** the release manifest reports missing or failed Windows code signing
- **THEN** the download center marks the build unavailable and does not render an active download action

#### Scenario: Verified package is downloaded
- **WHEN** a user chooses a verified package
- **THEN** the page presents the correct artifact plus checksum, minimum OS and installation help

#### Scenario: Owner publishes an explicitly labeled prototype test build
- **WHEN** an owner-authorized release workflow publishes an ad-hoc macOS arm64 artifact during the prototype stage
- **THEN** the page MAY expose it as a clearly labeled test build with checksum and installation warning, and MUST NOT describe it as signed, notarized or production-ready

### Requirement: Web download actions SHALL resolve through a server-controlled artifact URL
The Web client MUST receive a same-origin download URL and MUST NOT receive localhost paths, OSS credentials or permanent private-bucket URLs. The backend SHALL resolve the selected manifest entry and issue a short-lived OSS download redirect.

#### Scenario: User downloads the current macOS arm64 test build
- **WHEN** the user clicks the active download action on `/app/devices`
- **THEN** the browser requests the same-origin backend download endpoint and follows its short-lived OSS redirect to the exact manifest artifact

### Requirement: Runtime capability is distinct from package compatibility
The desktop companion SHALL report actual microphone, system-audio and protocol capabilities after installation. The Web interface MUST degrade to available input modes when a platform capability is absent and MUST NOT infer capture support solely from the downloaded package name.

#### Scenario: Windows app connects without system-audio capability
- **WHEN** a signed Windows x64 companion connects but reports system audio unavailable
- **THEN** the Web interface explains the limitation and keeps microphone, manual input and screenshot recovery paths available

### Requirement: Release manifest is controlled and rollbackable
Only an authorized release workflow SHALL publish, replace or withdraw manifest entries. Clients SHALL reject incompatible protocol versions and SHALL continue to provide a safe manual-input path.

#### Scenario: Release is withdrawn after discovery
- **WHEN** administrators withdraw a compromised or faulty artifact
- **THEN** new download requests no longer receive its URL and existing clients receive an upgrade or safety notice according to policy
