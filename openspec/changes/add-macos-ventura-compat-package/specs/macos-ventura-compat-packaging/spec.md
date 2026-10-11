## ADDED Requirements

### Requirement: Isolated Ventura 13.4 arm64 package

The repository MUST provide a local packaging command that keeps the desktop application version at 1.3.2, targets macOS arm64, declares macOS 13.4 as the minimum system version, and writes artifacts outside the official production release directory.

#### Scenario: Build a private compatibility artifact

- **WHEN** the Ventura compatibility packaging command completes successfully
- **THEN** it MUST produce a DMG in `apps/desktop/release/macos-compat-13.4-arm64/`
- **AND** the packaged application MUST report `LSMinimumSystemVersion` as 13.4.0 or lower
- **AND** the main executable and native capture runtime MUST be arm64
- **AND** the artifact metadata MUST identify version 1.3.2 and `developmentOnly: true`

### Requirement: No online publication side effects

The compatibility packaging command MUST NOT modify the official production manifest, upload files to OSS, or change Web download state.

#### Scenario: Keep official release state unchanged

- **WHEN** the private compatibility package is built
- **THEN** files under `apps/desktop/release/macos-production/` MUST NOT be replaced
- **AND** no publication command MUST be invoked
