## ADDED Requirements

### Requirement: Database-free accepted-frame path
An authenticated accepted audio frame SHALL NOT synchronously query or write PostgreSQL before reaching its bounded ASR queue.

#### Scenario: Contiguous frame arrives
- **WHEN** connection-time authorization remains valid and the next sequence is accepted
- **THEN** session-local state admits the frame without a database round trip

### Requirement: Entity-scoped Redis recovery
Realtime recovery state SHALL use session, publisher and device scoped keys or hashes and SHALL NOT serialize an application-wide snapshot for frame activity.

#### Scenario: One interview publishes audio
- **WHEN** its publisher or channel receipt advances
- **THEN** unrelated interview, device and heartbeat records are neither locked nor rewritten

### Requirement: Cold-path persistence isolation
Final transcript history, usage, tracing and audit persistence SHALL execute after realtime publication and SHALL NOT delay the incremental delivery event.

#### Scenario: PostgreSQL is temporarily slow
- **WHEN** an optional final-history write exceeds its latency budget
- **THEN** live transcript and answer-token delivery continue while the cold-path job retries or records a bounded failure
