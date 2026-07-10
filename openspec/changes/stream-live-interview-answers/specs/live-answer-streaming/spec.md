## ADDED Requirements

### Requirement: Live answer generation MUST support incremental answer events
The system MUST provide a live-answer streaming path that emits ordered answer events while the model is generating. The stream MUST include enough task metadata for the frontend to bind chunks to the correct interview session, question, and answer task.

#### Scenario: Stream starts for a manual question
- **WHEN** a user submits a manual question from an active interview session with streaming enabled
- **THEN** the backend creates a live answer task and emits a task-started event before answer chunks are emitted

#### Scenario: Model emits answer chunks
- **WHEN** the model produces partial answer text
- **THEN** the backend emits ordered chunk events that include sequence number, text, and whether the chunk is final

#### Scenario: Stream completes
- **WHEN** the model finishes successfully
- **THEN** the backend emits a completed event with the final task status and persisted answer text

### Requirement: The frontend MUST render streamed answer text as it arrives
The live interview page MUST display streamed answer chunks in the right-side answer area as soon as they are received. The user MUST NOT need to wait for the full answer to complete before seeing useful text.

#### Scenario: First chunk arrives
- **WHEN** the first answer chunk is received for a live answer task
- **THEN** the answer area shows that text immediately while the answer status remains generating or streaming

#### Scenario: Additional chunks arrive
- **WHEN** additional chunks are received for the same task
- **THEN** the answer area appends or reconciles them in sequence without duplicating text

#### Scenario: Stream finishes
- **WHEN** the completed event arrives
- **THEN** the answer status changes to completed and the final answer remains visible in the same answer slot

### Requirement: Streaming cancellation MUST stop new visible content
The system MUST support stopping an in-progress streamed answer. Once cancellation is accepted, the frontend MUST stop consuming or displaying new chunks for that task, and the backend MUST mark the task as cancelled or otherwise ignore late provider chunks.

#### Scenario: User stops a streaming answer
- **WHEN** the user clicks stop answer while chunks are arriving
- **THEN** the frontend stops updating the visible answer for that task and calls the backend cancellation endpoint

#### Scenario: Late chunk arrives after cancellation
- **WHEN** a provider chunk arrives after cancellation has been accepted
- **THEN** the system does not append that chunk to the visible completed answer

### Requirement: Streaming failures MUST preserve partial answer and retry context
If streaming fails after one or more chunks, the system MUST preserve the original question and any already displayed partial answer while clearly marking the task as failed. The frontend MUST expose a retry path without creating a false completed answer.

#### Scenario: Provider fails after partial output
- **WHEN** the provider stream fails after emitting partial answer text
- **THEN** the answer area keeps the partial text, marks the task failed, and shows a safe error message

#### Scenario: User retries a failed streamed answer
- **WHEN** the user retries a failed streamed answer
- **THEN** the retry starts a new live-answer task for the same question rather than mutating the failed task into a completed state

### Requirement: Streaming event data MUST protect sensitive configuration and source material
Streaming events MUST NOT expose server-side API keys, full prompts, raw resume/JD/knowledge content, or internal provider payloads. Events MAY include task status, chunk text, safe error messages, source summaries, model name, and request identifiers.

#### Scenario: Frontend receives stream event
- **WHEN** the frontend receives any live answer stream event
- **THEN** the event contains only the task state and safe answer content required to render the response
