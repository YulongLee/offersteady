## ADDED Requirements

### Requirement: Preserve truthful permission and late results
The companion SHALL distinguish pending/unknown, granted, denied and unavailable permissions. Timeout MUST NOT imply denial. A current late OS result SHALL be applied, while old lifecycle results MUST NOT overwrite replacement state. Windows MUST NOT report unconditional granted without an OS or media result.

#### Scenario: User allows after the UI waiting interval
- **WHEN** a current permission request remains pending beyond 2.5 seconds and later resolves granted
- **THEN** UI remains pending beforehand and applies granted once without duplicate requests

#### Scenario: Permission or device is unavailable
- **WHEN** OS denial, missing input or device read failure occurs
- **THEN** explicit permission denial is distinguished from device availability, with actionable retry and no fake grant

### Requirement: Synchronize changes without extra polling
Current permission changes SHALL update the local snapshot and existing registration promptly with in-flight deduplication and retry-on-existing-cycle behavior. Dedicated mock mode SHALL check and show microphone requirements only; ordinary/written workflows SHALL preserve their required sources.

#### Scenario: Grant arrives after initial unknown registration
- **WHEN** current permission changes to granted
- **THEN** one merged existing registration reflects it without waiting for a new periodic loop or changing heartbeat frequency

#### Scenario: Mock mode is bound
- **WHEN** a mock session is recognized and checked
- **THEN** screen/system audio requirements do not block or mislead the mock user, and ordinary source checks remain available for ordinary sessions

### Requirement: Preserve the approved existing appearance
Permission recovery SHALL use existing controls and automatic lifecycle refresh. The new standalone recheck button and extra permission notice block SHALL NOT be shown. Existing error-state microphone retry SHALL remain functional; removing presentation MUST NOT undo truthful permissions, late results or capability synchronization.

#### Scenario: Normal microphone row
- **WHEN** the companion displays its normal microphone controls
- **THEN** it preserves the existing row appearance and shows no newly added standalone recheck button or notice block

#### Scenario: Existing error retry
- **WHEN** a user selects the existing microphone retry after an input error
- **THEN** it still invokes the recovered permission/audio path and does not duplicate native permission requests
