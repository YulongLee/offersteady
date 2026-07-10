## ADDED Requirements

### Requirement: The system MUST provide one unified chat service for AI interview answers
The system SHALL provide one unified Chat Service that accepts a user question together with Interview Session context and returns AI-generated interview answer output for the approved prototype flow.

#### Scenario: Chat request starts from an interview question
- **WHEN** an authorized client submits a user question for a live interview session
- **THEN** the system MUST invoke one chat service entrypoint instead of requiring the client to assemble prompt, retrieval, and model calls itself

#### Scenario: Chat service stays scoped to answer generation
- **WHEN** the service processes a question
- **THEN** it MUST own prompt construction, model invocation, streaming output, conversation recording, and usage accounting for that answer request

### Requirement: The chat service MUST consume Interview Session as the authoritative conversation context
The system SHALL use Interview Session as the authoritative state source for session metadata, approved material scope, configuration snapshot, and multi-turn conversation context.

#### Scenario: Chat request references an interview session
- **WHEN** a chat request includes a session identifier
- **THEN** the system MUST load session-owned configuration and conversation context rather than relying on client-side reconstructed history

#### Scenario: Chat request continues a multi-turn interview
- **WHEN** the same session has prior interviewer turns, candidate turns, or AI advice entries
- **THEN** the chat service MUST be able to include the relevant multi-turn session context in the answer-generation flow

### Requirement: The chat service MUST integrate retrieval context without coupling to retrieval internals
The system SHALL call Knowledge Retrieval Service as an independent dependency and consume its structured context output when building AI interview answers.

#### Scenario: Retrieval context is available
- **WHEN** the chat service receives a question for a session with approved Resume, JD, or Knowledge materials
- **THEN** it MUST be able to request retrieval context and include the returned structured evidence in prompt construction

#### Scenario: Retrieval is unavailable or returns empty context
- **WHEN** retrieval fails, times out, or returns no relevant context
- **THEN** the chat service MUST degrade gracefully without requiring direct vector-store access or retrieval-specific fallback logic in the client

### Requirement: The chat service MUST build prompts through a dedicated prompt builder and template boundary
The system SHALL use a dedicated Prompt Builder and Prompt Template boundary so that prompt assembly, prompt versioning, and prompt configuration can change without rewriting chat orchestration logic.

#### Scenario: Prompt is built from question and session inputs
- **WHEN** a chat request begins
- **THEN** the system MUST build the final model input from the user question, session context, retrieval context, and configured prompt template through a prompt builder layer

#### Scenario: Prompt configuration changes
- **WHEN** the configured prompt template or prompt version changes
- **THEN** the chat service MUST be able to apply the new prompt configuration without changing the public Chat API contract

### Requirement: The chat service MUST support configurable model gateway selection
The system SHALL isolate model invocation behind a replaceable LLM Gateway so the product can use Qwen Chat API first while retaining the ability to switch providers later.

#### Scenario: Default provider uses Qwen
- **WHEN** the first production-capable chat provider is configured
- **THEN** the chat service MUST be able to call Qwen Chat API through the LLM Gateway boundary

#### Scenario: Provider is replaced later
- **WHEN** deployment changes to a different LLM provider
- **THEN** the chat orchestration and Chat API contract MUST remain stable while the provider adapter changes behind the gateway

### Requirement: The chat service MUST support streaming answer output
The system SHALL support streaming response output so the approved prototype can show AI answer content incrementally in the real-time answer area.

#### Scenario: Streaming answer is enabled
- **WHEN** a chat request is processed in streaming mode
- **THEN** the system MUST deliver ordered answer chunks and a clear completion signal for the same answer task

#### Scenario: Streaming answer stops before completion
- **WHEN** the model call fails, times out, or is cancelled before full completion
- **THEN** the system MUST return a terminal status that distinguishes incomplete output from a successful completed answer

### Requirement: The chat service MUST persist conversation history and answer records at session scope
The system SHALL store user questions, AI answer records, answer status, and related metadata as session-scoped conversation history rather than as transient client-only state.

#### Scenario: Successful answer is recorded
- **WHEN** a chat request completes successfully
- **THEN** the system MUST persist the question, the answer record, and relevant metadata in conversation storage for that interview session

#### Scenario: Interrupted or failed answer is recorded
- **WHEN** a chat request is interrupted, fails, or retries
- **THEN** the system MUST persist answer status and minimal operational metadata without pretending the answer completed successfully

### Requirement: The chat service MUST record token usage for each chat request
The system SHALL capture token usage for each answer-generation request and attribute it to the corresponding Interview Session.

#### Scenario: Provider returns usage data
- **WHEN** the LLM provider reports prompt, completion, or total token usage
- **THEN** the chat service MUST record that usage against the current session and answer request

#### Scenario: Usage is consumed by other services
- **WHEN** downstream billing, analytics, or session APIs read chat usage
- **THEN** the system MUST expose session-scoped usage facts rather than provider-local opaque counters only

### Requirement: The chat service MUST emit structured logs without exposing full sensitive content
The system SHALL emit operationally useful chat logs while excluding full prompts, full answers, or full private document content from ordinary logs.

#### Scenario: Chat request succeeds or fails
- **WHEN** a chat request starts, streams, succeeds, retries, or fails
- **THEN** the system MUST log structured metadata such as request id, session id, provider, prompt version, usage counters, duration, stream status, and error classification

#### Scenario: Sensitive content is protected in logs
- **WHEN** chat logs are recorded
- **THEN** they MUST NOT include full prompt text, full answer bodies, or full retrieved sensitive document chunks in ordinary logs

### Requirement: The chat service MUST support retry boundaries without changing prototype interaction
The system SHALL support retry behavior for transient provider or transport failures while preserving the approved prototype interaction and clear answer state transitions.

#### Scenario: Transient provider failure is retried
- **WHEN** the provider fails with a retryable transient error
- **THEN** the system MUST be able to retry within configured limits and preserve answer-task state consistency

#### Scenario: Retry budget is exhausted
- **WHEN** retry attempts are exhausted or the error is non-retryable
- **THEN** the system MUST return a final failed answer status and record the failure without silently hiding the error

### Requirement: The chat service MUST remain decoupled from screenshot and speech pipelines
The system SHALL provide interview answer generation for text-based chat inputs without directly owning Screenshot or Speech workflows in this change.

#### Scenario: Screenshot is out of scope
- **WHEN** the Screenshot pipeline is not implemented in this change
- **THEN** the chat service contract MUST remain valid without requiring screenshot-specific inputs

#### Scenario: Speech is out of scope
- **WHEN** speech capture or transcription pipelines are not implemented in this change
- **THEN** the chat service MUST still operate correctly for manual or already-normalized text questions
