## ADDED Requirements

### Requirement: Protocol-correct Qwen Audio streaming transport
The Backend SHALL connect `qwen-audio-3.0-asr-flash-streaming` through the DashScope inference-task WebSocket protocol and SHALL send PCM as binary frames only after `task-started`.

#### Scenario: Warm source task starts successfully
- **WHEN** the service warms a microphone or system-audio source using the Qwen Audio task protocol
- **THEN** it connects to the configured public `/api-ws/v1/inference` endpoint, sends `run-task`, waits for `task-started`, and marks only that source ready

#### Scenario: Audio frame uses binary transport
- **WHEN** an accepted application frame contains 16 kHz mono PCM
- **THEN** the adapter sends the PCM bytes as bounded binary WebSocket chunks without base64 JSON encoding or persistence

### Requirement: Partial and final transcript mapping
The adapter SHALL map non-empty `result-generated` events into monotonic application transcript revisions and SHALL treat `sentence_end=true` as authoritative text for the current segment.

#### Scenario: Provider emits an intermediate result
- **WHEN** `result-generated` contains non-empty text with `sentence_end=false`
- **THEN** the adapter publishes it through the existing partial listener for the current source and segment without waiting for another audio frame

#### Scenario: Provider completes a segment
- **WHEN** the application sends a terminal frame and the provider returns an authoritative sentence followed by `task-finished`
- **THEN** the adapter returns one final transcript for that segment and prevents later events from reopening it

#### Scenario: Provider emits heartbeat or empty sentence-begin
- **WHEN** `result-generated` has heartbeat semantics or empty text
- **THEN** the adapter records no visible transcript revision

### Requirement: Source isolation and bounded recovery
The system SHALL keep provider task state isolated by interview session and source and SHALL close only the affected provider connection after an ambiguous or failed task.

#### Scenario: One source task fails
- **WHEN** the microphone provider task returns `task-failed`
- **THEN** the microphone adapter raises a classified provider error and recreates its connection on retry without closing or altering the system-audio source

#### Scenario: Final result exceeds its wait budget
- **WHEN** the provider does not return authoritative completion within the configured finalization timeout
- **THEN** the adapter closes that source connection and delegates retry/incomplete handling to the existing realtime service

### Requirement: Explicit reversible provider selection
The Backend SHALL select the Qwen Audio task adapter or legacy Qwen3 Realtime adapter from server-side configuration and SHALL retain the prior model path as an explicit rollback option.

#### Scenario: New protocol is selected
- **WHEN** `OFFERSTEADY_REALTIME_ASR_PROTOCOL=qwen-audio-task`
- **THEN** dependency wiring uses the inference-task adapter with the configured streaming model and public inference endpoint

#### Scenario: Legacy protocol is restored
- **WHEN** `OFFERSTEADY_REALTIME_ASR_PROTOCOL=qwen3-realtime`
- **THEN** dependency wiring uses the existing Qwen3 Realtime adapter without requiring a code rollback

### Requirement: Privacy-safe provider observability
The adapter SHALL expose source-scoped connection, task, partial, final, timeout, and provider error counters without recording PCM, API keys, or transcript content.

#### Scenario: Diagnostics are inspected
- **WHEN** operations reads runtime ASR diagnostics
- **THEN** it can identify the selected protocol/model and lifecycle outcomes while no audio bytes, credentials, or transcript text appear in the diagnostic payload
