## ADDED Requirements

### Requirement: Measure and minimize quick-answer first display latency
The quick-answer flow SHALL record server admission, executor admission, provider first token, SSE yield, browser receipt, and browser render timestamps, and SHALL avoid avoidable work before the first visible answer.

#### Scenario: First answer token is available
- **WHEN** the provider returns the first answer token
- **THEN** the client receives a visible answer without waiting for the detail stage or full response completion

#### Scenario: Latency diagnostics are submitted
- **WHEN** the first answer is rendered
- **THEN** the performance acknowledgement includes available stage timestamps and remains backward compatible when optional timestamps are absent

#### Scenario: Provider is slow or unavailable
- **WHEN** the provider exceeds the configured response budget or fails
- **THEN** the user receives a clear retryable state and the stream executor is released without a leaked task
