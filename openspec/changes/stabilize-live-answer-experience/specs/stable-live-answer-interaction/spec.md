## ADDED Requirements

### Requirement: Current answer follows the newest owned task
The system SHALL make a newly initiated answer task the current answer immediately and MUST NOT allow an older snapshot, callback, or terminal event to replace a newer current task.

#### Scenario: Explicit quick answer becomes current immediately
- **WHEN** the user starts a quick answer while another answer is visible
- **THEN** the workspace immediately displays the submitted question and its pending answer state
- **AND** later updates from the previous task do not replace it

#### Scenario: Older workspace snapshot arrives late
- **WHEN** a workspace history refresh containing an older active task arrives after a newer local or streamed task
- **THEN** the older records are merged into history without changing the current task or reducing its answer text

#### Scenario: User is intentionally viewing history
- **WHEN** a new explicitly requested answer arrives while the user is viewing a historical answer
- **THEN** the explicitly requested answer becomes current and the historical answer remains available through navigation

### Requirement: Answer task state and text progress monotonically
The system SHALL merge updates for the same answer task by revision and lifecycle stage, and SHALL preserve the longest valid streamed prefix so stale updates cannot move the task backward or shorten visible content.

#### Scenario: Stale generating update follows completion
- **WHEN** a completed task is followed by a stale generating update for the same task
- **THEN** the task remains completed and its final answer remains visible

#### Scenario: Shorter stream fragment arrives late
- **WHEN** the workspace has displayed a streamed prefix and later receives an older shorter prefix
- **THEN** the displayed answer is not shortened or replaced by a placeholder

### Requirement: Streamed answers render smoothly
The system SHALL batch small answer-stream updates into short visual intervals while retaining the latest received content, and MUST flush final, failed, cancelled, or stopped states immediately.

#### Scenario: Many small chunks arrive rapidly
- **WHEN** multiple answer chunks arrive faster than a user can perceive individual updates
- **THEN** the workspace renders grouped progressive updates without clearing existing text or repeatedly flashing loading placeholders

#### Scenario: Stream finishes inside a render interval
- **WHEN** a terminal answer event arrives before the next scheduled visual update
- **THEN** the final state and complete available text are rendered immediately

#### Scenario: No detailed section is generated
- **WHEN** an answer finishes with only a simple section
- **THEN** the workspace does not continue displaying a message that claims detailed content is still being generated

#### Scenario: Internal question normalization state changes
- **WHEN** a question moves from normalization pending to completed or fallback while its answer is visible
- **THEN** the workspace keeps normalization metadata internal and does not insert an additional normalization label above the question
- **AND** the question heading does not shift because of that internal state transition

#### Scenario: Unrelated realtime transcript update arrives during an answer
- **WHEN** microphone or system-audio partial transcripts update while the visible answer text is unchanged
- **THEN** the answer body is not reparsed or structurally rebuilt

#### Scenario: Markdown answer is still streaming
- **WHEN** an incomplete Markdown fragment is received during answer generation
- **THEN** the workspace updates it in a stable text container without repeatedly rebuilding lists, code blocks, or formulas
- **AND** applies full Markdown formatting once the answer reaches a terminal completed state

### Requirement: Quick answer provides explicit operation feedback
The system SHALL present quick answer as a visually identifiable button and SHALL communicate ready, processing, success, and failure states next to or within the action while preventing duplicate in-flight submission.

#### Scenario: Quick answer uses detected interviewer question
- **WHEN** the input is empty and a complete recent interviewer question exists
- **THEN** the quick-answer button is available and submits that detected question once
- **AND** the button shows an in-progress state until the request reaches a terminal state

#### Scenario: Quick answer has no usable question
- **WHEN** both manual input and a usable detected interviewer question are absent
- **THEN** the system does not submit a request and explains what the user needs to do

#### Scenario: Quick answer fails
- **WHEN** the quick-answer request fails
- **THEN** the action area reports the failure and allows a deliberate retry without silently duplicating the failed request

### Requirement: Screenshot answer provides explicit staged feedback
The system SHALL present screenshot answer as a visually identifiable button and SHALL expose capture, upload, recognition, generation, completion, failure, and cancellation feedback while preventing duplicate active capture requests.

#### Scenario: Screenshot answer starts
- **WHEN** the user activates screenshot answer
- **THEN** a current placeholder answer is created immediately
- **AND** the action reports the active screenshot stage until completion

#### Scenario: Screenshot action is already active
- **WHEN** the user activates screenshot answer while the same screenshot workflow is still active
- **THEN** the system keeps the existing workflow and does not create a duplicate request

#### Scenario: Screenshot answer fails or is cancelled
- **WHEN** capture, upload, recognition, or generation fails or the user cancels it
- **THEN** the button area and current answer show the terminal state and provide a safe retry path

### Requirement: Answer generation requires an explicit user action
The system SHALL use realtime speech only to update transcripts and identify interviewer-question candidates. It MUST NOT start an answer task or bill answer generation until the user explicitly activates quick answer or screenshot answer.

#### Scenario: Complete final interviewer question arrives
- **WHEN** the system channel produces a final, high-confidence interviewer question
- **THEN** the system records and confirms the candidate without starting an answer task
- **AND** quick answer can use that question after the user activates it

#### Scenario: User has not selected an answer action
- **WHEN** transcripts and confirmed question candidates continue to arrive without a quick-answer or screenshot-answer action
- **THEN** no answer task, assistant context, answer usage, or answer-stream event is created

#### Scenario: User explicitly activates quick answer
- **WHEN** the user activates quick answer with a manual question or usable recent interviewer question
- **THEN** the system starts exactly one answer task for that explicit action

#### Scenario: User explicitly activates screenshot answer
- **WHEN** the user activates screenshot answer and the screenshot workflow succeeds
- **THEN** the system starts exactly one screenshot answer task for that explicit action

### Requirement: Interaction regressions use synthetic data
The system MUST verify current-task ownership, stream ordering, the no-automatic-answer boundary, quick answer, and screenshot feedback using synthetic or anonymized fixtures and SHALL NOT add logs containing complete real interview questions, answers, audio, or screenshot bodies.

#### Scenario: Regression suite runs
- **WHEN** the live-answer regression tests execute
- **THEN** they use synthetic questions and task identifiers and cover late events, duplicate events, action feedback, and terminal states
