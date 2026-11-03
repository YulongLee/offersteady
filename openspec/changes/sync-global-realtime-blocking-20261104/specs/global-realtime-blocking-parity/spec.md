## ADDED Requirements

### Requirement: Bounded Global audio work
Global SHALL isolate synchronous audio work and lifecycle operations in independent bounded lanes, drain admitted work on cancellation, clean abandoned publisher results once and preserve per-session capture order and existing Global terminal handling.

#### Scenario: Slow work and caller cancellation
- **WHEN** synthetic Redis or ASR work is delayed and the caller cancels repeatedly
- **THEN** unrelated loop work continues, bounded capacity is preserved and admitted creation/cleanup is neither replayed nor abandoned

### Requirement: Atomic state and constant pinned reads
Global SHALL use entity atomic state updates without holding a process-wide I/O lock, retain owner/version/retirement/seed/TTL semantics, and resolve valid complete pins without whole-history scanning.

#### Scenario: Large synthetic history
- **WHEN** valid pins are queried with 1, 1191 and 10000 historical bindings
- **THEN** transport and decoding work remain constant and server-wide HVALS/HGETALL/HSCAN on the hit path remain zero

#### Scenario: Stale or cross owner pin
- **WHEN** identity, generation, owner, retirement or authoritative DB status invalidates a pin
- **THEN** the original rejection/latest fallback semantics hold and stale or foreign sessions never become usable

### Requirement: Operation local material reuse and Global preservation
Global SHALL batch/deduplicate document metadata inside the original operation, preserve ownership/version/fingerprint checks and retain original time memberships, Creem, language, mock, resume, models, settings and routes.

#### Scenario: Changed material on next operation
- **WHEN** a document changes, disappears or changes owner between operations
- **THEN** the next operation uses current authorized data and no cross-request cached document is returned

#### Scenario: Existing Global journeys
- **WHEN** synthetic ordinary, written, mock, commerce and language regressions execute
- **THEN** existing outcomes and full API/Settings contracts remain compatible
