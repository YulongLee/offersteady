## ADDED Requirements

### Requirement: Runtime actions carry correlated timing identifiers
The system SHALL correlate client intent, desktop capture, backend processing, provider first text/final completion, event publication, and browser render using opaque trace identifiers and timestamps.

#### Scenario: Quick answer renders
- **WHEN** the browser renders the first and final text for an explicitly triggered quick answer
- **THEN** the system can calculate intent-to-first-render and intent-to-final-render without storing the question or answer text

#### Scenario: Screenshot answer renders
- **WHEN** a screenshot answer progresses from click through capture and model completion
- **THEN** the system can calculate request-to-claim, capture, upload, model-first-text, completion, event, and render durations for the same trace

### Requirement: Performance telemetry excludes sensitive content
Performance telemetry MUST NOT include raw audio, transcript text, question text, answer text, screenshot bytes/base64, resume/JD/knowledge contents, model secrets, access tokens, phone numbers, or user-visible filenames.

#### Scenario: Telemetry acknowledgement is submitted
- **WHEN** a browser or desktop client reports a render or capture timing stage
- **THEN** the backend accepts only allow-listed identifiers, numeric durations/timestamps, source/status enums, and safe error codes

### Requirement: Telemetry failure cannot interrupt an interview
Telemetry recording SHALL be best-effort, bounded, and isolated from audio ingest, answer streaming, screenshot completion, and billing.

#### Scenario: Telemetry storage is unavailable
- **WHEN** the metrics store times out or rejects a record
- **THEN** the active interview workflow continues and only a safe operational warning is emitted
