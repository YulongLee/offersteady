## ADDED Requirements

### Requirement: Unified session event envelope
The system SHALL publish transcript, explicit answer, and screenshot lifecycle changes through a session-scoped event stream with a stable event identifier, session identifier, owner identifier, event kind, creation time, payload, and monotonically advancing stream cursor.

#### Scenario: Ordered event delivery
- **WHEN** multiple state transitions occur in one live interview session
- **THEN** subscribers receive events with unique event identifiers and a cursor that never moves backwards

#### Scenario: Duplicate delivery
- **WHEN** a reconnect or parallel transport delivers the same logical task update more than once
- **THEN** the client merges it idempotently and does not regress the visible task status or answer text

### Requirement: Snapshot hydration and event continuation
The system SHALL send an authoritative snapshot when a live session subscription starts and SHALL continue with incremental events after the snapshot cursor.

#### Scenario: First subscription
- **WHEN** a user opens an active interview without a valid stored cursor
- **THEN** the stream returns the current transcripts, candidates, answer state, screenshot state, runtime state, and a continuation cursor

#### Scenario: Reconnect after interruption
- **WHEN** a subscriber reconnects with a retained cursor
- **THEN** the system delivers changes after that cursor or returns a fresh authoritative snapshot when the cursor can no longer be resumed safely

### Requirement: Explicit answer lifecycle events
The system SHALL publish answer task lifecycle events only for answers explicitly requested by the user through quick answer, manual answer, or screenshot answer controls. Speech transcription and question confirmation MUST NOT create an answer task.

#### Scenario: Speech produces a question candidate
- **WHEN** the realtime speech service confirms an interviewer question and the user has not selected an answer action
- **THEN** the system publishes transcript or candidate state without creating or publishing an answer task

#### Scenario: User requests quick answer
- **WHEN** the user explicitly selects quick answer
- **THEN** the dedicated answer stream and unified session stream may both carry the task but the client presents one monotonically advancing answer

### Requirement: Screenshot lifecycle events
The system SHALL publish every persisted screenshot capture transition needed by the web client, without placing screenshot binary content in the event payload.

#### Scenario: Remote screenshot completes
- **WHEN** a remote screenshot request moves through requested, claimed, uploaded, processing, and completed states
- **THEN** the session stream exposes those states for the same request identifier and includes the completed answer summary

#### Scenario: Remote screenshot fails
- **WHEN** capture, upload, vision, or answer generation fails
- **THEN** the stream publishes a terminal failed state with a safe stage and safe user-facing error message

### Requirement: Recovery-only historical reconciliation
The web client SHALL use the unified stream as the primary source for an active interview and SHALL use history or task query endpoints only for initial hydration, explicit history navigation, or bounded recovery after stream failure.

#### Scenario: Healthy active stream
- **WHEN** the live session event stream remains connected
- **THEN** the client does not run a parallel high-frequency screenshot or answer status polling loop

#### Scenario: Stream unavailable
- **WHEN** the session stream disconnects while a screenshot task is pending
- **THEN** the client performs non-overlapping bounded exponential-backoff reconciliation and stops it when the stream recovers or the task becomes terminal
