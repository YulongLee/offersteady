# Desktop production release

## ADDED Requirements

### Requirement: Publish aligned 1.3.0 release manifests

For both the domestic and Global production editions, the public release manifest MUST contain exactly one 1.3.0 entry for each supported target: macOS arm64, macOS x64, and Windows x64.

#### Scenario: Public state exposes the new version

- **WHEN** an anonymous client requests the edition's web state after publication
- **THEN** every supported target reports version `1.3.0`, protocol version `2.0`, and a valid download URL

### Requirement: Preserve platform trust metadata

macOS production entries MUST report verified signing and notarization. Windows entries MUST report the existing unsigned/local-development signing state and MUST NOT claim notarization.

#### Scenario: Trust status is truthful

- **WHEN** a client reads the release manifest
- **THEN** macOS entries are marked verified/notarized and Windows is explicitly unsigned/not notarized

### Requirement: Keep previous releases recoverable

Publication MUST retain prior release artifacts and preserve rollback metadata until the new release has passed public probes.

#### Scenario: Publication fails part way through

- **WHEN** any artifact fails validation or upload
- **THEN** the affected edition's manifest is not switched to a partial release
