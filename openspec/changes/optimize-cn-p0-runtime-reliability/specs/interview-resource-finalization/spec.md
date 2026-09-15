## ADDED Requirements

### Requirement: Finalize interview resources
The system SHALL make interview end, cancellation, and idle expiration idempotently stop session-scoped ASR providers, SSE/event waiters, desktop transports, executors, and ephemeral buffers.

#### Scenario: User ends an active interview
- **WHEN** an active interview is ended
- **THEN** all session-scoped resources are released or scheduled for bounded cleanup and the session is no longer counted as active

#### Scenario: End request is repeated
- **WHEN** an already-ended interview receives another end or cleanup request
- **THEN** the operation succeeds without creating duplicate workers or errors

#### Scenario: Cleanup is observable
- **WHEN** cleanup runs
- **THEN** metrics expose active resources, reclaimed sessions, and cleanup failures without exposing transcript or personal data
