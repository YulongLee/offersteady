## ADDED Requirements

### Requirement: Quick answer MUST normalize fragmented interviewer speech
The system MUST use the existing quick-answer model call to organize the current interviewer turn into one complete question without adding facts or changing intent.

#### Scenario: Fragmented interviewer turn is normalized
- **WHEN** the user starts quick answer from multiple current-session interviewer transcript fragments
- **THEN** the system produces one complete normalized question before generating the detailed answer

#### Scenario: Question contains a contextual reference
- **WHEN** the interviewer question contains a reference such as “这个方案” that can be resolved from recent session conversation
- **THEN** the normalized question resolves the reference only from that recent context and does not invent missing details

### Requirement: Raw and normalized questions MUST remain distinguishable
The system MUST retain the submitted raw transcript text separately from the normalized display question and MUST record whether normalization completed or fell back.

#### Scenario: Normalization succeeds
- **WHEN** the model returns a valid non-empty normalized question
- **THEN** the answer task stores both raw and normalized questions with status `completed`

#### Scenario: Normalization output is invalid
- **WHEN** the model omits the required structure or returns an empty or unsafe normalized question
- **THEN** the answer task uses the cleaned raw question with status `fallback` and does not expose protocol markers

### Requirement: Answer stages MUST share the normalized question
The system MUST use the normalized question for the visible title, quick answer, detailed answer, and knowledge retrieval query.

#### Scenario: Knowledge material is selected
- **WHEN** normalization succeeds and the detailed answer retrieves selected knowledge material
- **THEN** embedding, reranking, and Top3 retrieval use the normalized question

#### Scenario: Web receives normalization during streaming
- **WHEN** the backend resolves the normalized question before answer completion
- **THEN** the Web answer header updates to the normalized question while answer text continues streaming

### Requirement: Historical tasks MUST remain compatible
The system SHALL display existing answer tasks that do not contain normalization fields by using their legacy question value.

#### Scenario: Legacy answer history is loaded
- **WHEN** a stored answer task has no raw or normalized question fields
- **THEN** the Web displays the task question and does not fail history loading

### Requirement: Question normalization MUST be evaluated with synthetic data
The system MUST include synthetic evaluations for fragmented speech, repetition, contextual references, multiple subquestions, and malformed model output.

#### Scenario: Evaluation fixtures are inspected
- **WHEN** the question normalization evaluation set is loaded
- **THEN** every record is marked synthetic and contains no real user transcript or personal material
