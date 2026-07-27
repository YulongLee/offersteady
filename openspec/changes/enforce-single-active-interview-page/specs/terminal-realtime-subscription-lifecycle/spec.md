## ADDED Requirements

### Requirement: Lease identity protects realtime streams
The backend SHALL validate the page instance and lease generation when an active lease exists before opening and while maintaining a realtime stream.

#### Scenario: Stale stream is rejected before opening
- **WHEN** a page requests a stream using a superseded lease identity
- **THEN** the backend returns HTTP 409 and does not allocate a stream loop

#### Scenario: Open stream is revoked
- **WHEN** a newer page takes over while an older stream is open
- **THEN** the older stream receives a terminal revoked event and closes

### Requirement: Terminal failures do not reconnect
The Web application MUST treat HTTP 404, 409, 410 and SSE revocation as terminal for the current page instance.

#### Scenario: Replaced subscription terminates
- **WHEN** the realtime adapter reports HTTP 409 or an SSE revoked event
- **THEN** all heartbeat, polling and reconnect timers for that page are cleared

#### Scenario: Transient failure retries
- **WHEN** the realtime stream fails with a transient network or server error
- **THEN** the page uses bounded exponential retry while its lease remains active
