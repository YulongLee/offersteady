## ADDED Requirements

### Requirement: Preparation binding stays synchronized

The Global preparation page MUST refresh the authoritative desktop binding while mounted, without overlapping requests, and MUST stop refreshing when unmounted.

#### Scenario: Companion connects after preparation opens

- **WHEN** the preparation page is open and the Companion becomes bound
- **THEN** the page reflects the bound device within the refresh interval without requiring a full-page reload

#### Scenario: Binding endpoint is temporarily unavailable

- **WHEN** a refresh receives a non-404 API or network failure
- **THEN** the page shows a connectivity error and keeps the existing binding state available for retry

### Requirement: Global application releases are consistent

The Global deployment verification MUST reject a release when the Web and Backend containers were created from different Compose release directories.

#### Scenario: Web and Backend use different release directories

- **WHEN** post-deployment container labels identify different Compose working directories
- **THEN** deployment verification fails before the release is accepted

#### Scenario: Web and Backend use the same release directory

- **WHEN** both application containers identify the current Compose working directory
- **THEN** deployment verification continues to health and public smoke checks
