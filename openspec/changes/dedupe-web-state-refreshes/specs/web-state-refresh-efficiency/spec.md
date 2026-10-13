## ADDED Requirements

### Requirement: Merge concurrent Web state reads by authentication mode
The Web state adapter MUST share one in-flight `/api/v1/web/state` request among concurrent callers that use the same authentication mode.

#### Scenario: Concurrent authenticated reads
- **WHEN** two authenticated callers invoke `loadState` before the first request completes
- **THEN** the adapter sends one authenticated network request and resolves both callers with equivalent state values

#### Scenario: Public and authenticated reads remain isolated
- **WHEN** a public caller and an authenticated caller invoke `loadState` concurrently
- **THEN** the adapter sends separate requests with their respective authentication headers and does not share either result

### Requirement: Reuse only recent successful state
The Web state adapter MUST reuse a successful state result for no longer than 1.5 seconds for ordinary reads, MUST return an independent state value to each caller, and MUST NOT cache failures.

#### Scenario: Sequential reads inside the reuse window
- **WHEN** an ordinary caller invokes `loadState` within 1.5 seconds of a successful read with the same authentication mode
- **THEN** the adapter returns the recent state without sending another network request

#### Scenario: Expired state is read again
- **WHEN** an ordinary caller invokes `loadState` after the 1.5-second reuse window
- **THEN** the adapter sends a new network request

#### Scenario: Failed request is retried
- **WHEN** a state request fails and a caller invokes `loadState` again
- **THEN** the later call sends a new request instead of returning the previous failure from cache

### Requirement: Force refresh after authoritative changes
The Web state adapter MUST support a force-refresh option that bypasses the reuse window and replaces the cached state after a successful response.

#### Scenario: Mutation refresh bypasses cache
- **WHEN** a caller invokes `loadState` with `force: true` after a recent successful read
- **THEN** the adapter sends a new request and subsequent ordinary reads use the forced response

#### Scenario: Force refresh uses the requested authentication mode
- **WHEN** an authenticated caller requests a forced refresh
- **THEN** the adapter sends the request with the authenticated headers and does not replace the public cache
