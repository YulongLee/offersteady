## ADDED Requirements

### Requirement: All official CN clients publish one verified version
The CN release SHALL provide version 1.3.5 for macOS arm64, macOS x64 and Windows x64. Each artifact SHALL retain its existing platform identity, protocol and CN service defaults and SHALL exclude local/Global overrides and server credentials.

#### Scenario: A release candidate is a local test package
- **WHEN** a candidate includes local test service configuration or lacks formal Mac signing/publication verification
- **THEN** it cannot be published as the official Mac installer

#### Scenario: Mac installation artifacts are ready
- **WHEN** each Mac architecture is approved for publication
- **THEN** its DMG and contained app pass Developer ID, notarization, stapler/Gatekeeper and actual main/helper audio-input checks

#### Scenario: Windows installation artifact is ready
- **WHEN** the Windows package is prepared on a non-Windows build host
- **THEN** its actual payload is x64, its NSIS container and source contents are verified, and metadata does not claim a trusted signature or physical-device acceptance that was not performed

### Requirement: Public release changes are atomic and reversible
The public manifest SHALL switch to the new three-platform release only after all artifact uploads and integrity checks succeed. Existing download behavior and running interviews SHALL remain available, and prior manifest/object/image metadata SHALL be retained for rollback.

#### Scenario: One artifact upload or validation fails
- **WHEN** any platform is not ready
- **THEN** the existing public manifest remains active

#### Scenario: The manifest is refreshed at request time
- **WHEN** new metadata is ready
- **THEN** an atomic manifest replacement publishes all three entries without a business-container restart and retains restart-safe release materials

#### Scenario: Public downloads are checked
- **WHEN** release publication is verified
- **THEN** all three entries report 1.3.5 and their downloaded bytes match verified artifact size and SHA-256

### Requirement: Client publication remains within the authorized scope
Publication SHALL not deploy pending backend mock-generation changes, change billing, replace unrelated services or publish Global installers. Validation records SHALL distinguish structural/signature checks from physical-device microphone acceptance.

#### Scenario: A newer backend working-tree change exists
- **WHEN** client release metadata is published
- **THEN** the running backend business source remains its actual pre-release baseline, with only authorized release metadata updated
