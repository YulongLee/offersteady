## ADDED Requirements

### Requirement: Global Web state reads are coalesced and freshness-scoped

The Global Web adapter MUST coalesce concurrent `/api/v1/web/state` reads independently for public and authenticated callers. It MUST cache successful values for no more than 1.5 seconds, MUST NOT cache failures, and MUST return independent state values to callers.

#### Scenario: Concurrent authenticated reads

- **WHEN** multiple authenticated callers request state before the first request completes
- **THEN** the adapter performs one authenticated API request
- **AND** every caller receives an independent equivalent state value

#### Scenario: Public and authenticated isolation

- **WHEN** a public state read and an authenticated state read overlap or occur within the cache window
- **THEN** each uses its own request/cache key and authorization headers

#### Scenario: Authoritative refresh

- **WHEN** a login, logout, deletion, library-processing refresh, or billing synchronization requires current state
- **THEN** the caller bypasses the short cache with an explicit forced refresh

#### Scenario: Failure and cancellation

- **WHEN** a shared state request fails or an individual caller aborts
- **THEN** the failed value is not cached
- **AND** an individual abort does not cancel other callers waiting on the shared request

### Requirement: Global transcript telemetry is sampled without dropping final revisions

The Global Web MUST limit non-final `transcript-render` performance acknowledgements to at most one sample per five-second session window, while retaining final revisions and the existing diagnostic opt-in behavior.

#### Scenario: Frequent non-final revisions

- **WHEN** non-final transcript revisions arrive more frequently than five seconds for an interview
- **THEN** the Web sends at most one corresponding performance acknowledgement in that window

#### Scenario: Final revision

- **WHEN** a final transcript revision arrives inside a sampling window
- **THEN** the final revision remains eligible for acknowledgement

#### Scenario: Existing payload and delivery behavior

- **WHEN** telemetry sampling suppresses an acknowledgement
- **THEN** transcript rendering, answer generation, and realtime event delivery continue unchanged
- **AND** retained acknowledgements use the existing endpoint, payload shape, bounded queue, and idempotency rules
