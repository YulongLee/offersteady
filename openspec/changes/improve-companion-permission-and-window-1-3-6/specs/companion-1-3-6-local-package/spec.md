## ADDED Requirements

### Requirement: Deliver an installable local version without publishing
The local companion SHALL report version1.3.6, preserve CN app identity and use the existing HTTPS CN API/workspace. Packages SHALL contain exactly the verified architecture-specific runtime and tested dist, with actual signing/entitlement checks on Mac and PE/archive checks on Windows. No server keys or unintended local/global runtime overrides SHALL be included. Production services, official manifests, OSS objects and Global distribution MUST NOT be updated.

#### Scenario: User installs the new local companion
- **WHEN** the user exits the old companion and installs the provided package
- **THEN** the new instance reports1.3.6 and can use the existing CN binding protocol and website without deploying a server version

#### Scenario: Build and test evidence is delivered
- **WHEN** synthetic checks and package validation complete
- **THEN** output links, hashes and executed checks are recorded, physical-device and unnotarized/unsigned limits are truthful, and no real paid session or audio capture is claimed as tested automatically
