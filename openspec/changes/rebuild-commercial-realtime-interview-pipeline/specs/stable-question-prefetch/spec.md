## ADDED Requirements

### Requirement: Interviewer-only stable partial detection
The system SHALL derive stable question prefixes only from the interviewer channel and SHALL NOT treat candidate speech as a new interviewer question.

#### Scenario: Interviewer partial grows monotonically
- **WHEN** consecutive revisions share a sufficiently stable prefix
- **THEN** the detector publishes a higher stable revision suitable for predictive retrieval

#### Scenario: Candidate answers aloud
- **WHEN** candidate-channel partials and finals arrive
- **THEN** they remain captions/review context and do not replace the current interviewer question

### Requirement: Bounded parallel context prefetch
Stable interviewer text SHALL start or refresh bounded resume, JD and knowledge retrieval and SHALL cache the prepared result by session and predicted-question revision.

#### Scenario: Stable question changes materially
- **WHEN** a newer stable revision changes retrieval intent
- **THEN** obsolete prefetch work is cancelled or ignored and the newest compatible result becomes authoritative

#### Scenario: Prefetch is slow or fails
- **WHEN** prepared context is unavailable at answer activation
- **THEN** quick answer falls back to the existing on-demand retrieval path without blocking unrelated realtime delivery

### Requirement: Explicit immutable answer activation
Realtime understanding SHALL NOT start answer generation automatically. Quick answer SHALL freeze the authoritative question and compatible prefetch revision at the moment of user activation.

#### Scenario: User selects quick answer
- **WHEN** an authoritative candidate question is visible and the user activates quick answer
- **THEN** the answer task stores `questionId`, `questionRevision`, `questionText`, `clickedAtMs` and `prefetchRevision` before streaming the LLM response

#### Scenario: A later ASR revision arrives
- **WHEN** an answer task is already generating
- **THEN** the task continues using its frozen question snapshot and does not switch questions
