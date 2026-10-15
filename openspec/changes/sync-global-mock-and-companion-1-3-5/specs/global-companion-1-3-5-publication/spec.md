## ADDED Requirements

### Requirement: Independent Global audio recovery
Global Companion 1.3.5 SHALL use the stable Global identity, immutable Global HTTPS runtime configuration and English UI/permission declarations. Failed microphone capture SHALL retain its reason and support user retry without repeated automatic permission attempts. Capability registration SHALL preserve mock protocol and current permission state; level display SHALL use the same actual capture callback. Stopped or failed captures SHALL release resources idempotently.

#### Scenario: Permission or device is unavailable
- **WHEN** Global mock microphone setup fails
- **THEN** the English UI retains a useful reason and offers retry without misreporting silence as a connected capture

#### Scenario: Periodic capability update
- **WHEN** initial or periodic Global device registration runs
- **THEN** mock protocol and latest permission state remain present without reverting an already reported capability

### Requirement: Verify three production Global packages
Global macOS arm64, macOS x64 and Windows x64 packages SHALL be independently built as version 1.3.5 with correct architecture, Global runtime resources and no local-test or server-secret configuration. Mac App/native/helper/DMG signatures and audio input permissions SHALL be actually verified, notarized and stapled. Windows SHALL use its verified NSIS payload and truthfully retain unsigned status. Publication metadata SHALL be derived from verified final artifacts.

#### Scenario: A final Mac artifact is incomplete
- **WHEN** a signature, actual entitlement, notarization or Gatekeeper check fails
- **THEN** the package is not eligible for public release and metadata cannot claim verified/notarized

#### Scenario: Both editions build
- **WHEN** Global and CN/Beta packaging tests execute
- **THEN** Global uses English declarations and independent identity while existing CN/Beta defaults remain intact

### Requirement: Publish complete Global release with safe rollback
All three immutable Global objects SHALL pass complete size/SHA readback before the Global manifest advertises 1.3.5. Production updates SHALL preserve exact Global environment/model/data boundaries, protect active user work and retain original manifests/images/objects for rollback. Public version, MIME, range and complete downloads SHALL match the verified artifacts; production tests SHALL not create real-user sessions, charges or provider requests.

#### Scenario: One platform is not ready
- **WHEN** one required platform lacks a verified final package or complete object readback
- **THEN** the previous Global public manifest remains authoritative rather than advertising a partial release

#### Scenario: Verification succeeds and cutover is idle
- **WHEN** candidates and downloads pass and current protected user-work counts are zero
- **THEN** only authorized Global components are switched, public 1.3.5 artifacts are reachable, prior features remain, and rollback preserves user records and old objects
