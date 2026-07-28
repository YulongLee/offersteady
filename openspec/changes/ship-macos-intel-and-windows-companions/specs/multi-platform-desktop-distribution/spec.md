## ADDED Requirements

### Requirement: Reproducible target packages
The project SHALL provide explicit build commands for macOS arm64, macOS x64, and Windows x64 and SHALL emit a package plus metadata containing platform, architecture, version, size, SHA-256, signing status, and capabilities. The user-facing Windows package SHALL be a single NSIS installer with desktop and Start Menu shortcuts and an uninstall entry.

#### Scenario: Build unsigned Windows test package
- **WHEN** a maintainer runs the Windows x64 test packaging command
- **THEN** the release directory contains a Windows x64 installer and matching metadata marked as local development

### Requirement: Platform-scoped OSS storage
Desktop artifacts SHALL be stored under `desktop-releases/{platform}/{architecture}/{version}/` and the publisher SHALL preserve entries for other platform and architecture pairs.

#### Scenario: Publish Intel package after Apple Silicon package
- **WHEN** the Intel metadata is published
- **THEN** the release manifest contains both macOS arm64 and macOS x64 entries with distinct OSS object keys

### Requirement: Download center presents usable platform choices
The Web download center SHALL recommend a matching downloadable package when detectable and SHALL display platform-specific installation guidance and honest signing state.

#### Scenario: Windows user selects unsigned test release
- **WHEN** a Windows user selects an available local-development x64 entry
- **THEN** the page offers its download and explains the Windows extraction and SmartScreen flow without showing macOS instructions

### Requirement: Verified status is protected
The system MUST NOT mark a package verified without a valid checksum and required platform signing; macOS verified packages MUST also be notarized.

#### Scenario: Unsigned test package is published
- **WHEN** a package has no production signing identity
- **THEN** its manifest entry remains local-development and is visibly labeled as a test build
