## ADDED Requirements

### Requirement: Patch identity is unambiguous and UI invariant
The companion release SHALL identify as version 1.2.1 while preserving the existing bundle identifier `com.offersteady.companion`, product icon, renderer layout, styles, and interview workflow from 1.2.0.

#### Scenario: User opens the 1.2.1 production companion
- **WHEN** the signed packaged application starts
- **THEN** it reports version 1.2.1 with the existing production identity and displays the 1.2.0 layout without development-window chrome

#### Scenario: Release diff contains a UI change
- **WHEN** release verification detects an unapproved renderer layout, stylesheet, icon, or product-identity change
- **THEN** 1.2.1 packaging SHALL fail until the unrelated change is removed

### Requirement: Live-session restart resumes authoritative audio state
The 1.2.1 client and compatible gateway SHALL resume independent microphone and system channels from authoritative sequence offsets and source generations after a desktop process restart.

#### Scenario: Desktop restarts into the same live interview
- **WHEN** the backend has already accepted a channel generation and the replacement desktop connects
- **THEN** the next source starts above the backend generation and new frames receive acknowledgements without a stale-generation or sequence-gap retry loop

### Requirement: macOS production artifacts preserve trusted identity
The release SHALL provide Apple Silicon and Intel macOS artifacts using the existing Developer ID identity and Bundle ID, and each artifact SHALL pass Hardened Runtime, notarization, stapling, Gatekeeper, hash, and architecture verification.

#### Scenario: A macOS trust check fails
- **WHEN** signing, notarization, stapling, Gatekeeper, hash, architecture, or designated-requirement verification fails
- **THEN** the artifact SHALL NOT be described or delivered as a production 1.2.1 package

### Requirement: Privacy authorization remains user controlled
The companion SHALL request only the macOS microphone and screen/system-audio permissions required for enabled capture, SHALL retain a stable signed identity for upgrades, and SHALL NOT claim that an Apple developer account silently grants those permissions.

#### Scenario: Existing macOS grant is reusable
- **WHEN** 1.2.1 replaces an earlier build with the same Bundle ID and designated signing requirement and macOS retains the grant
- **THEN** capture starts without asking the user to authorize the same service again

#### Scenario: macOS requires authorization
- **WHEN** TCC reports that a required capture service is not authorized
- **THEN** the companion reports the missing permission and directs the user to System Settings instead of looping or falsely reporting capture success

### Requirement: Local artifact delivery is separate from production publication
The release workflow SHALL build and verify immutable local 1.2.1 artifacts without modifying the production download manifest or deploying services unless production publication is explicitly authorized.

#### Scenario: Local release artifacts pass verification
- **WHEN** the requested local 1.2.1 build completes
- **THEN** artifact paths, hashes, architectures, and signing status are reported while the production manifest remains unchanged

### Requirement: Authorized production publication is atomic and recoverable
After explicit owner authorization, the release workflow SHALL upload immutable 1.2.1 artifacts before atomically switching the production manifest, SHALL deploy only the compatible Backend service, and SHALL retain the 1.2.0 manifest and prior Backend image as rollback points.

#### Scenario: Artifact publication fails
- **WHEN** an artifact upload, checksum, signature, or manifest validation fails
- **THEN** the production manifest SHALL remain on 1.2.0 and the Backend SHALL NOT be deployed

#### Scenario: Production rollout succeeds
- **WHEN** all immutable artifacts and manifest entries validate and Backend deployment completes
- **THEN** public health, web state, version entries, download range requests, artifact checksums, and the realtime resume handshake SHALL be verified before 1.2.1 is declared live

#### Scenario: Production validation fails after deployment
- **WHEN** a required public health or realtime compatibility check fails
- **THEN** the deployment SHALL restore the retained Backend image and 1.2.0 manifest without restarting PostgreSQL, Redis, or Web

### Requirement: Release evidence protects interview privacy
Release verification SHALL use synthetic fixtures and metadata-only health, signature, hash, and transport counters and SHALL NOT store or publish interview audio, transcript text, screenshots, secrets, or personal information.

#### Scenario: Verification evidence is recorded
- **WHEN** automated or physical acceptance evidence is written
- **THEN** it contains only non-content metadata and redacted identifiers
