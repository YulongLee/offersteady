## ADDED Requirements

### Requirement: Manual live questions MUST call the backend chat model chain
The system SHALL submit manual questions from the live interview page to the backend Live Answer / Chat Service for the current Interview Session instead of generating a synthetic answer in the frontend.

#### Scenario: User submits a manual question during a live interview
- **WHEN** the user enters a question in the live interview question box and clicks "回答问题"
- **THEN** the frontend MUST call the backend live-answer question endpoint with the current session identifier and question text

#### Scenario: Frontend does not synthesize manual answers
- **WHEN** a manual question is submitted
- **THEN** the frontend MUST NOT create a completed answer, fake model output, or final advice content without a backend response

### Requirement: Manual answer generation MUST use the current Interview Session context
The system SHALL generate manual-question answers using the current Interview Session as the authoritative context source, including confirmed Resume, JD, Knowledge Base, model configuration, prompt configuration, and retrieval configuration.

#### Scenario: Session has confirmed materials
- **WHEN** the backend receives a manual question for a session with confirmed Resume, JD, or Knowledge materials
- **THEN** the backend MUST use the session-bound material scope through Chat Service and Retrieval boundaries rather than relying on prompt content assembled in the frontend

#### Scenario: Session has no selected materials
- **WHEN** the backend receives a manual question for a session without selected materials
- **THEN** the system MUST still answer using the configured chat model and clearly avoid fabricating candidate-specific experience

### Requirement: Manual answer status MUST be backend-authoritative
The system SHALL treat backend task state as the source of truth for manual answer generation, completion, failure, cancellation, and displayed answer content.

#### Scenario: Backend returns a generated answer
- **WHEN** the backend returns answer text, chunks, metadata, and completed task status
- **THEN** the live answer area MUST display that answer and include it in answer history

#### Scenario: Backend returns a queued or streaming task
- **WHEN** the backend returns a non-terminal answer task
- **THEN** the live answer area MUST show an in-progress state tied to the backend task identifier

#### Scenario: Backend returns a failed task or request error
- **WHEN** the backend fails to generate an answer or rejects the request
- **THEN** the live answer area MUST show a real failure state and MUST NOT replace it with a fake successful answer

### Requirement: Manual answer history MUST persist at session scope
The system SHALL persist manual questions and generated answers through backend conversation storage so they are available after refresh and during interview review.

#### Scenario: User refreshes after generating a manual answer
- **WHEN** the user reloads the product after a manual answer has completed
- **THEN** the answer history MUST be restored from backend session state or backend answer history, not from local-only state

#### Scenario: User opens interview review
- **WHEN** the user reviews a session with manual questions
- **THEN** the review page MUST include backend-recorded manual questions and answers for that session

### Requirement: Manual answer cancellation MUST target backend tasks
The system SHALL cancel in-progress manual answers by calling the backend task cancellation endpoint and rendering the returned cancellation state.

#### Scenario: User stops an in-progress manual answer
- **WHEN** the user clicks the answer stop control for an in-progress manual answer
- **THEN** the frontend MUST call the backend cancellation endpoint with the active backend task identifier

#### Scenario: Cancellation succeeds
- **WHEN** the backend confirms the answer task is cancelled
- **THEN** the live answer area MUST mark the matching answer as cancelled without fabricating a completed answer

### Requirement: Manual answer billing and usage MUST not be faked by the frontend
The system SHALL rely on backend-returned usage, billing, or refreshed aggregate state as the authoritative source for manual-answer consumption.

#### Scenario: Manual answer request starts
- **WHEN** the user submits a manual question
- **THEN** the frontend MAY show pending consumption feedback but MUST NOT treat local point deduction as the authoritative successful settlement

#### Scenario: Backend records usage
- **WHEN** the backend records token usage or billing usage for a manual answer
- **THEN** the next loaded product state MUST reflect backend-authoritative usage facts

### Requirement: Manual question flow MUST preserve the approved live page interaction
The system SHALL keep the approved live interview page layout and action placement while connecting manual questions to the model chain.

#### Scenario: User enters the live page after preparing a session
- **WHEN** the user enters the live interview page after creating an interview and confirming materials
- **THEN** the page MUST remain usable for manual question input without requiring local desktop software readiness checks

#### Scenario: User uses the compact question bar
- **WHEN** the user views the live interview page on desktop or mobile
- **THEN** the "回答问题" action MUST remain in the existing compact question bar and continue to trigger manual model answering
