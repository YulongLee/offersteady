## ADDED Requirements

### Requirement: Retire logically before bounded physical close
CN ordinary realtime cleanup SHALL retain authoritative end/billing/fences and detach/close the old source logically before deferring its physical handshake into bounded capacity. Accepted cleanup MUST not be dropped or target a replacement connection.

#### Scenario: Slow old connection close
- **WHEN** physical close blocks while the same source reconnects or a different session starts
- **THEN** the old source cannot emit usable late data, new connection preparation proceeds and the deferred job closes only its captured old object

#### Scenario: Full queue or shutdown
- **WHEN** close capacity is full, admission is closed, a close raises, or shutdown begins
- **THEN** memory/threads stay bounded, synchronous fallback preserves cleanup, accepted jobs drain without cancellation and fixed numeric failure evidence remains

### Requirement: Preparation has independent bounded capacity
CN publisher prepare/create SHALL use a bounded lane independent of lifecycle and ingress while preserving ordering, exception contracts, cancellation drain and one-time abandoned publisher cleanup. Global/mock and original synchronous gateway methods MUST remain compatible.

#### Scenario: Lifecycle jobs occupy both workers
- **WHEN** both lifecycle workers are slow and the caller starts or cancels a publisher prepare/create
- **THEN** preparation can execute in its own fixed capacity and admitted creation/compensation is performed exactly once
