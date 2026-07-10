## ADDED Requirements

### Requirement: Interview sessions persist confirmed material snapshots
The system SHALL persist a session-level material snapshot whenever the user confirms materials for an interview. The snapshot MUST include document IDs, document version IDs, material kinds, display names, index states, safe summaries and confirmation time.

#### Scenario: User confirms selected materials
- **WHEN** a user confirms one Resume, one JD and multiple Knowledge materials on the preparation page
- **THEN** the backend saves a session material snapshot containing the selected document versions and returns the updated selection revision

#### Scenario: Backend restarts after confirmation
- **WHEN** the backend process restarts after a material snapshot has been confirmed
- **THEN** the interview session still loads the confirmed material snapshot from persistent storage

### Requirement: Answers use only the confirmed session snapshot
The system SHALL assemble live answer and screenshot answer context only from the current confirmed session material snapshot. The system MUST NOT automatically use newly uploaded, deleted, replaced or unconfirmed library materials in an existing answer.

#### Scenario: User uploads a new document after starting an interview
- **WHEN** the user uploads another Knowledge document after the current session has already confirmed materials
- **THEN** new answers in that session do not use the new document unless the session materials are explicitly reconfirmed before the answer

#### Scenario: Session has no confirmed materials
- **WHEN** a user asks a question in a session with no confirmed materials or a confirmed empty list
- **THEN** the answer records that no selected material was used and avoids candidate-specific claims not present in the question

### Requirement: Resume and JD are fixed context while Knowledge is RAG context
The system SHALL load confirmed Resume and JD Markdown as fixed Prompt context, and SHALL retrieve only confirmed Knowledge materials through embedding search and rerank for RAG context. A zero retrieved chunk count MUST NOT imply that Resume or JD fixed context was unused.

#### Scenario: Resume-only question
- **WHEN** a session has a confirmed Resume and the user asks about their strengths
- **THEN** the answer service loads the Resume as fixed context and records it as a used fixed source even when no Knowledge chunks are retrieved

#### Scenario: Knowledge-only retrieval
- **WHEN** a session has confirmed Knowledge materials and the user asks a related technical question
- **THEN** retrieval searches only those confirmed Knowledge document versions and records retrieved sources when relevant chunks are found

### Requirement: Answer provenance distinguishes used, retrieved and unavailable materials
The system SHALL return safe provenance for every completed, degraded or failed answer task. Provenance MUST distinguish fixed sources, retrieved sources, unavailable selected sources, retrieval counts and truncation state without exposing full document text, prompts or embeddings.

#### Scenario: Answer uses fixed and retrieved sources
- **WHEN** an answer uses confirmed Resume, JD and retrieved Knowledge chunks
- **THEN** the response includes fixed source count, retrieved source count and safe source labels for each used material

#### Scenario: Selected material is unavailable at answer time
- **WHEN** a confirmed source cannot be loaded, read or retrieved during answer assembly
- **THEN** the answer task records the unavailable source and the generated response MUST NOT claim that the source was used

### Requirement: Material-grounded answers do not fabricate candidate facts
The answer prompt SHALL instruct the model to prioritize confirmed material context for candidate-specific claims and MUST prohibit inventing company names, projects, metrics, responsibilities or skills that are absent from the confirmed materials and user question.

#### Scenario: Requested fact is present
- **WHEN** confirmed materials contain a relevant candidate project fact
- **THEN** the answer grounds its candidate-specific claim in that fact

#### Scenario: Requested fact is absent
- **WHEN** confirmed materials do not contain the requested candidate-specific detail
- **THEN** the answer states the limitation and offers a safe answer strategy rather than fabricating details
