## ADDED Requirements

### Requirement: Production live tasks use shared transient storage
The production system SHALL store chat-answer tasks, screenshot-answer tasks, capture requests, and non-sensitive upload metadata in shared Redis storage with bounded TTL, while tests MAY use in-memory adapters.

#### Scenario: Backend process is replaced
- **WHEN** a backend process restarts while another client reads an existing terminal task
- **THEN** the task remains readable from shared storage until its configured TTL expires

#### Scenario: In-flight work is interrupted
- **WHEN** a process disappears while a task is queued or generating and no provider worker can continue it
- **THEN** the task becomes failed and retryable within a bounded recovery interval instead of remaining indefinitely in progress

### Requirement: Sensitive media remains ephemeral
The shared task store MUST NOT contain raw PCM, screenshot bytes, screenshot base64 data, access tokens, or complete diagnostic payloads.

#### Scenario: Screenshot metadata is persisted
- **WHEN** screenshot task or upload metadata is written to Redis
- **THEN** only identifiers, safe filenames/types, sizes, hashes, stages, timestamps, billing references, and answer task state are stored

### Requirement: Task updates cannot regress
The repository SHALL reject a stale update that would replace a newer revision, shorten accumulated output, or move a terminal task back into an active state.

#### Scenario: Two backend workers update the same task
- **WHEN** an older worker writes after a newer terminal update
- **THEN** the persisted terminal task remains authoritative
