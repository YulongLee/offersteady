## ADDED Requirements

### Requirement: Current companion required for interview entry
The CN system MUST reject a desktop device whose reported version is lower than the newest published release for the same platform and architecture, or whose version cannot be verified, when binding or starting an interview.

#### Scenario: outdated companion
- **WHEN** a device reports a parseable older version
- **THEN** the API returns HTTP 409 with error code `companion_update_required` and tells the user to download the latest companion before continuing.

#### Scenario: current or newer companion
- **WHEN** the CN device version is equal to or newer than the matching published release
- **THEN** the request is not blocked by the version gate.

#### Scenario: unknown companion version
- **WHEN** the CN device version, platform or architecture is missing, malformed or has no matching published release
- **THEN** the API returns HTTP 409 with error code `companion_update_required` and asks the user to install the latest companion.

#### Scenario: preparation page explains and enforces the gate
- **WHEN** a user opens the CN interview preparation page
- **THEN** the machine-code area states that the latest companion is required, links to the download center, and an already-bound outdated device cannot enable the start action.

### Requirement: Low-overhead heartbeat
The system MUST NOT enumerate all device bindings on every desktop heartbeat.

#### Scenario: heartbeat
- **WHEN** a known device sends a heartbeat
- **THEN** only its device record is updated and no binding-list query is issued by the heartbeat handler.

### Requirement: Bounded control-plane polling
The system MUST use a 10-second normal polling budget for preparation heartbeats, desktop active-connection polling and backend control-query caching.

#### Scenario: normal control-plane polling
- **WHEN** a current client remains on preparation or waits for an active binding
- **THEN** it waits approximately 10 seconds between normal requests and the backend may reuse the authoritative query result for that interval.
