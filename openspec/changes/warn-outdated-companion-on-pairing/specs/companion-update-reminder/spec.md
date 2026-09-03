## ADDED Requirements

### Requirement: Connected outdated companions receive a matching update reminder
After a desktop companion is successfully bound on an interview or written-exam preparation page, the Web client SHALL compare its reported application version with the latest downloadable release for the same reported platform and architecture. When the connected version is older, the page SHALL display the current and latest versions and offer the matching controlled download action.

#### Scenario: Older matching companion connects
- **WHEN** a companion reporting a parseable version, platform and architecture binds successfully and a newer downloadable release exists for that exact target
- **THEN** the preparation page displays a non-blocking update reminder with the current version, latest version and matching download action

#### Scenario: Current or newer companion connects
- **WHEN** the connected companion version is equal to or newer than the latest matching release
- **THEN** the preparation page does not display an update reminder

### Requirement: Update reminders never block preparation
The update reminder SHALL allow the user to continue using the connected companion and SHALL NOT change readiness, prevent interview entry, request new permissions or modify realtime capture behavior.

#### Scenario: User continues with current version
- **WHEN** the user dismisses the reminder by choosing to continue with the current version
- **THEN** the reminder is hidden for that binding and the existing start flow remains available

#### Scenario: Version cannot be determined
- **WHEN** version, platform or architecture information is missing, unsupported or malformed, or no matching downloadable release exists
- **THEN** the page omits the reminder and preserves the existing connection and start behavior

### Requirement: Version checking reuses existing preparation data
The Web client MUST derive the update state from the existing device binding response and release manifest already loaded in application state. It MUST NOT add polling, heartbeat frequency, or a separate version-check request.

#### Scenario: Preparation page evaluates a connected device
- **WHEN** binding or release-manifest state changes
- **THEN** the Web client recomputes the reminder locally without issuing an additional network request
