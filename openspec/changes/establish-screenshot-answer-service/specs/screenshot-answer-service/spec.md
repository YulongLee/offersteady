## ADDED Requirements

### Requirement: The system MUST provide one unified screenshot answer service
The system SHALL provide one unified Screenshot Answer Service that accepts screenshot inputs plus Interview Session context and returns AI-generated answer output for screenshot-based interview assistance.

#### Scenario: Screenshot answer request starts from the live interview flow
- **WHEN** an authorized client submits one or more screenshots for an active interview session
- **THEN** the system MUST invoke one screenshot answer entrypoint instead of requiring the client to separately coordinate upload, vision, prompt assembly, and answer generation

#### Scenario: Screenshot answer stays scoped to screenshot-based answering
- **WHEN** the service processes screenshot inputs
- **THEN** it MUST own image handling, vision understanding, prompt construction, streaming answer output, conversation recording, and usage attribution for that screenshot answer request

### Requirement: The screenshot answer service MUST support image upload and preprocessing
The system SHALL support screenshot upload and preprocessing so screenshot answer requests can safely accept images before model inference begins.

#### Scenario: Screenshot upload is accepted
- **WHEN** a user confirms screenshot submission from the live workspace
- **THEN** the system MUST register the uploaded image inputs and make them available to the screenshot answer task

#### Scenario: Screenshot preprocessing runs before model invocation
- **WHEN** a screenshot answer task begins
- **THEN** the system MUST be able to validate and preprocess the images before sending them to the vision model

### Requirement: The screenshot answer service MUST support multiple screenshots in one answer request
The system SHALL support one screenshot answer request containing multiple ordered screenshot inputs so that users can submit complex or multi-step problems without leaving the approved prototype flow.

#### Scenario: Multiple screenshots belong to one answer task
- **WHEN** the client submits multiple screenshots for the same request
- **THEN** the system MUST preserve their order within one screenshot answer task rather than treating them as unrelated separate answers by default

#### Scenario: Partial image set is unavailable
- **WHEN** one image in the submitted set fails validation or processing
- **THEN** the system MUST return a clear failure or degradation state for the screenshot answer task rather than silently ignoring the missing image

### Requirement: The screenshot answer service MUST consume Interview Session as the authoritative session context
The system SHALL use Interview Session as the authoritative source of session identity, approved material scope, configuration snapshot, and conversation context for screenshot answers.

#### Scenario: Screenshot answer request references an interview session
- **WHEN** a screenshot answer request includes a session identifier
- **THEN** the system MUST load the session-owned context rather than relying on the client to reconstruct session state

#### Scenario: Screenshot answer is restored later
- **WHEN** the user reopens a session with prior screenshot answer history
- **THEN** the system MUST be able to return the persisted screenshot-answer records as part of the session-scoped history model

### Requirement: The screenshot answer service MUST integrate retrieval context without coupling to retrieval internals
The system SHALL call Knowledge Retrieval Service independently and consume structured Resume, JD, and Knowledge context to enhance screenshot answers when relevant materials exist.

#### Scenario: Session has approved materials
- **WHEN** the screenshot answer service runs for a session with approved Resume, JD, or Knowledge materials
- **THEN** it MUST be able to request retrieval context and use the returned structured context to enhance the screenshot answer

#### Scenario: Retrieval is unavailable or empty
- **WHEN** retrieval fails, times out, or returns no relevant context
- **THEN** the screenshot answer service MUST degrade gracefully without requiring direct vector-store access in the screenshot path

### Requirement: The screenshot answer service MUST isolate vision model invocation behind a replaceable gateway
The system SHALL isolate image understanding behind a provider-agnostic Vision Gateway so the product can use Qwen Vision first while retaining the ability to switch visual model providers later.

#### Scenario: Default vision provider uses Qwen Vision
- **WHEN** the first production-capable visual provider is configured
- **THEN** the screenshot answer service MUST be able to call Qwen Vision through the Vision Gateway boundary

#### Scenario: Vision provider changes later
- **WHEN** deployment switches to a different visual model provider
- **THEN** the screenshot answer orchestration and Screenshot Chat API contract MUST remain stable while the provider adapter changes behind the gateway

### Requirement: The screenshot answer service MUST build prompts through a dedicated prompt builder boundary
The system SHALL use a dedicated prompt builder and prompt template boundary so screenshot-derived vision context, retrieval context, and session context can be assembled consistently without hard-coding prompt logic in API handlers.

#### Scenario: Prompt is built from screenshot and session inputs
- **WHEN** a screenshot answer request begins
- **THEN** the system MUST build the final model input from the screenshot-derived understanding, session context, retrieval context, and configured prompt template through a prompt builder layer

#### Scenario: Prompt template changes
- **WHEN** the prompt template or prompt configuration changes
- **THEN** the screenshot answer service MUST be able to apply the new prompt configuration without changing the public Screenshot Answer API contract

### Requirement: The screenshot answer service MUST support streaming answer output
The system SHALL support streaming answer output so the approved prototype can display screenshot-based answers incrementally in the live answer area.

#### Scenario: Streaming screenshot answer is enabled
- **WHEN** a screenshot answer task is processed in streaming mode
- **THEN** the system MUST deliver ordered answer chunks and a clear completion signal for that screenshot answer task

#### Scenario: Screenshot answer fails before completion
- **WHEN** visual or generation stages fail, time out, or are interrupted before completion
- **THEN** the system MUST return a terminal status that distinguishes incomplete output from a completed screenshot answer

### Requirement: The screenshot answer service MUST persist screenshot answer history at session scope
The system SHALL persist screenshot answer records, screenshot-related metadata, answer status, and related context references as session-scoped history rather than transient client-only state.

#### Scenario: Screenshot answer completes successfully
- **WHEN** a screenshot answer task completes successfully
- **THEN** the system MUST persist the screenshot answer record and related metadata under the current interview session

#### Scenario: Screenshot answer fails or retries
- **WHEN** a screenshot answer task fails or retries
- **THEN** the system MUST preserve status and minimal operational metadata without pretending that a final successful answer exists

### Requirement: The screenshot answer service MUST record usage and logs without exposing full sensitive content
The system SHALL record token usage and structured operational logs for screenshot answer tasks while excluding full screenshots, full prompts, and full answer bodies from ordinary logs.

#### Scenario: Usage is returned by the provider
- **WHEN** the provider reports prompt, visual, completion, or total usage for a screenshot answer
- **THEN** the system MUST attribute that usage to the corresponding interview session and screenshot answer task

#### Scenario: Logs are recorded
- **WHEN** screenshot answer logs are emitted
- **THEN** they MUST include structured metadata such as request id, session id, answer task id, provider, prompt version, image count, duration, status, and error code, but MUST NOT include full image bodies or full answer text in ordinary logs

### Requirement: The screenshot answer service MUST remain decoupled from speech workflows
The system SHALL provide screenshot-based answering without directly depending on speech capture or transcription pipelines in this change.

#### Scenario: Speech is out of scope
- **WHEN** speech workflows are not implemented in this change
- **THEN** the screenshot answer contract MUST remain valid for screenshot-driven answering without requiring speech inputs
