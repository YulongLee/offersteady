## ADDED Requirements

### Requirement: Live answer startup reuses one authoritative session snapshot
The system SHALL validate the active interview session and its bound-material state once for one explicit live-answer startup, and SHALL reuse that snapshot while persisting the question and building the prompt.

#### Scenario: Quick answer starts with selected materials
- **WHEN** a user requests a quick answer in a live session with selected resume, JD, or knowledge materials
- **THEN** the system uses the same validated session snapshot for admission, question persistence, history selection, and prompt construction without changing the selected-material evidence

#### Scenario: A later answer observes material changes
- **WHEN** the material binding changes after one answer operation completes
- **THEN** the next answer operation performs a new authoritative session read and observes the new binding

### Requirement: Commercial admission behavior remains authoritative
The system MUST complete the existing idempotent answer-usage reservation before requesting answer tokens and MUST preserve balance, membership, settlement, release, retry, and duplicate-request behavior.

#### Scenario: Insufficient balance
- **WHEN** the existing billing policy rejects an answer reservation for insufficient balance
- **THEN** the provider is not called and the user receives the existing safe billing error

#### Scenario: Duplicate quick-answer command
- **WHEN** the same idempotency key is submitted more than once
- **THEN** the system does not charge more than once and preserves the existing task behavior

### Requirement: Provider connections are safely reusable
The Qwen-compatible gateway SHALL reuse a bounded server-side HTTP connection pool across answer requests while preserving the configured endpoint, model, authentication, timeout, retry, streaming, and error mapping behavior.

#### Scenario: Consecutive streaming stages
- **WHEN** a quick stage is followed by a detailed or continuation stage
- **THEN** both stages can reuse the gateway connection pool and emit the same ordered answer content as before

#### Scenario: Provider connection failure
- **WHEN** a pooled provider connection becomes unusable
- **THEN** the HTTP client reconnects within the existing timeout and the gateway applies the existing retryable or non-retryable error policy

### Requirement: First-visible-answer latency is measurable without content
The system SHALL correlate browser intent, backend startup, provider request, first raw token, first visible SSE answer event, browser receive, and browser render with opaque identifiers and content-free timing metadata.

#### Scenario: First answer text renders
- **WHEN** the browser renders the first non-empty quick-answer text
- **THEN** it sends one best-effort acknowledgement that allows click-to-first-render latency to be measured

#### Scenario: Telemetry failure
- **WHEN** performance telemetry storage or acknowledgement fails
- **THEN** the answer stream continues without changing answer status, content, billing, or cancellation behavior

#### Scenario: Sensitive content exclusion
- **WHEN** answer timing is recorded
- **THEN** the telemetry contains no question text, answer text, prompt, transcript, resume, JD, knowledge content, credential, phone number, or filename

### Requirement: Existing answer semantics remain unchanged
The optimization MUST preserve question normalization, Chinese and English routing, programming-language policy, selected-material grounding, quick and detailed answer order, cancellation, retry, history recovery, and terminal task persistence.

#### Scenario: Existing behavior regression suite
- **WHEN** the optimized live-answer path is tested with Chinese, English, programming, material-grounded, cancelled, retried, and recovered tasks
- **THEN** observable answer content, ordering, billing, and terminal states match the previous contract
