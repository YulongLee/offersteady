## ADDED Requirements
### Requirement: Public homepage Companion downloads
The Global homepage SHALL provide login-free Windows and macOS download controls below existing primary actions using the canonical Global release catalogue.
#### Scenario: Desktop visitor downloads
- **WHEN** a visitor selects Windows or expands macOS and selects Apple Silicon or Intel
- **THEN** the matching published Global package uses the existing same-origin download endpoint without creating an account or session
#### Scenario: Unsafe or unavailable release
- **WHEN** a manifest entry is withdrawn, development-only, lacks a valid checksum or has a non-Global filename
- **THEN** no download link for that entry is generated and unavailable platforms show a disabled state
#### Scenario: Mobile and assistive use
- **WHEN** the visitor uses a narrow viewport or keyboard
- **THEN** controls remain accessible without page overflow; only platform buttons and Mac architecture choices are shown, without helper descriptions
#### Scenario: Static discovery
- **WHEN** the homepage is fetched without JavaScript
- **THEN** the same released platform links are present in initial HTML without extra helper descriptions
### Requirement: Isolated release
The change SHALL leave core services and China unchanged.
#### Scenario: Deployment
- **WHEN** the approved change is released
- **THEN** only Global Web is recreated with rollback retained and existing public download links verified
