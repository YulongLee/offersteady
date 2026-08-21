## ADDED Requirements

### Requirement: Screenshot vision delivery defaults to ephemeral inline data
The system SHALL submit validated and optimized screenshot bytes to the configured vision model as inline image data by default and SHALL NOT write those screenshot bytes to product object storage.

#### Scenario: Default screenshot answer
- **WHEN** a bound desktop companion uploads a valid screenshot for a live interview and the server uses the default delivery mode
- **THEN** the backend SHALL call the vision model with inline image data without saving the screenshot to OSS

#### Scenario: Existing answer behavior remains unchanged
- **WHEN** the inline vision request succeeds
- **THEN** the system SHALL preserve the current screenshot-only prompt, answer ordering, billing settlement and session event behavior

### Requirement: Ephemeral screenshot bytes are released after terminal processing
The system SHALL retain screenshot bytes only for the active screenshot-answer task and MUST remove them from the transient upload store after the task completes, fails or is cancelled.

#### Scenario: Vision answer completes
- **WHEN** a screenshot answer reaches the completed state
- **THEN** the corresponding image bytes SHALL no longer be available from the transient upload store

#### Scenario: Vision answer fails
- **WHEN** all screenshot vision attempts fail
- **THEN** the corresponding image bytes SHALL be removed while non-sensitive failure metadata remains available

### Requirement: Screenshot content is excluded from logs and events
The system MUST NOT include raw screenshot bytes, Base64 image data or reusable image URLs in application logs, diagnostics or session events.

#### Scenario: Inline request is observed
- **WHEN** the backend records screenshot timing and delivery telemetry
- **THEN** it SHALL record only non-content metadata such as delivery mode, dimensions, byte counts, hashes, stage durations and error codes

### Requirement: Operators can roll back to object-storage delivery
The system SHALL provide a server-side configuration that switches screenshot vision delivery between `inline` and the existing `oss` compatibility mode without changing clients.

#### Scenario: OSS compatibility mode enabled
- **WHEN** an operator configures screenshot vision delivery as `oss`
- **THEN** the backend SHALL save the optimized screenshot, generate a short-lived signed URL and submit that URL through the existing vision adapter

#### Scenario: Unsupported delivery mode configured
- **WHEN** the service starts with a screenshot delivery mode outside the supported values
- **THEN** configuration validation SHALL fail instead of silently selecting a storage behavior
