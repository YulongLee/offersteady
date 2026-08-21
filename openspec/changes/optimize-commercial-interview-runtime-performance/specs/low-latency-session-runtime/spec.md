## ADDED Requirements

### Requirement: Session events wake consumers without fixed empty polling
The production Redis event repository SHALL support a bounded blocking wait for events after a cursor while preserving snapshot, keepalive, lease validation, and cursor-expiry recovery.

#### Scenario: New event is published
- **WHEN** a connected web or desktop consumer waits after the current cursor and a new session event is appended
- **THEN** the wait returns promptly without waiting for a fixed 100 millisecond polling boundary

#### Scenario: No event is published
- **WHEN** no event arrives within the bounded wait period
- **THEN** the route regains control to check disconnect, authorization lease, and keepalive requirements without emitting an error

### Requirement: Non-final audio append does not wait for provider output
The realtime ASR pipeline SHALL append ordered non-final PCM to the persistent provider session without synchronously waiting for a new partial transcript, while final frames MUST still wait for an authoritative completion or bounded failure.

#### Scenario: Provider partial is delayed
- **WHEN** the provider has not emitted new text after a non-final audio append
- **THEN** the source ingest worker remains available for later ordered frames and does not block for the partial timeout

#### Scenario: Final frame is committed
- **WHEN** the desktop sends a final frame after the configured silence boundary
- **THEN** the backend waits for the provider final event and publishes exactly one authoritative final transcript or a safe retryable failure

### Requirement: Detailed-answer retrieval is prefetched safely
The system SHALL begin retrieval during quick-answer generation when possible, without delaying quick first text or changing the final selected-material and retrieval policy.

#### Scenario: Normalized question remains equivalent
- **WHEN** quick-stage normalization preserves the raw question meaning and retrieval key
- **THEN** the detailed stage reuses the prefetched retrieval result

#### Scenario: Question normalization changes retrieval meaning
- **WHEN** the normalized question is not equivalent to the prefetched query
- **THEN** the system retrieves again with the normalized question before generating the detailed answer
