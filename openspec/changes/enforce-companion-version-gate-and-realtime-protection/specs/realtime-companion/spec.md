## ADDED Requirements

### Requirement: Current companion required for interview entry
The system MUST reject a desktop device whose reported version is lower than the newest published release for the same platform and architecture when binding or starting an interview.

#### Scenario: outdated companion
- **WHEN** a device reports a parseable older version
- **THEN** the API returns HTTP 409 with error code `companion_update_required` and tells the user to download the latest companion before continuing.

#### Scenario: current, newer, or unknown companion
- **WHEN** the version is equal/newer, missing, malformed, or no matching published release exists
- **THEN** the request is not blocked by the version gate.

### Requirement: Low-overhead heartbeat
The system MUST NOT enumerate all device bindings on every desktop heartbeat.

#### Scenario: heartbeat
- **WHEN** a known device sends a heartbeat
- **THEN** only its device record is updated and no binding-list query is issued by the heartbeat handler.
