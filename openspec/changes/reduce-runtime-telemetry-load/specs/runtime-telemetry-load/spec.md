## ADDED Requirements

### Requirement: Intermediate transcript telemetry is bounded
The Web client SHALL send at most one non-final transcript-render acknowledgement per session sampling window and SHALL retain the final revision acknowledgement.

#### Scenario: Continuous subtitle updates
- **WHEN** multiple non-final subtitle revisions render within five seconds
- **THEN** at most one non-final performance acknowledgement is sent for that session
- **AND** the interview UI continues rendering each revision locally

#### Scenario: Final subtitle revision
- **WHEN** a final revision renders after a sampled non-final revision
- **THEN** the final performance acknowledgement is still sent

### Requirement: Telemetry authorization does not reread full session state for every sample
The backend SHALL reuse a short-lived positive ownership check for transcript-render telemetry and SHALL preserve full ownership validation for answer and screenshot acknowledgement stages.

#### Scenario: Repeated transcript-render acknowledgements
- **WHEN** repeated acknowledgements arrive for the same owned session within the cache window
- **THEN** only the first request performs the full session lookup
- **AND** later requests remain content-free and are accepted for the same owner

#### Scenario: Non-owner telemetry request
- **WHEN** a transcript-render acknowledgement uses a different authenticated owner
- **THEN** the backend rejects it and does not record telemetry

### Requirement: User-facing interview behavior is unchanged
Telemetry sampling or caching SHALL NOT block, delay or alter audio capture, transcription, answer generation, screenshot assistance, billing or session state transitions.

#### Scenario: User continues an active interview
- **WHEN** a telemetry acknowledgement is sampled or served from cache
- **THEN** the live interview remains usable and all product events continue through their existing paths
