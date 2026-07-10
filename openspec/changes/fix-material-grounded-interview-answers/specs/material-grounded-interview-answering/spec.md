## ADDED Requirements

### Requirement: Answers assemble confirmed materials before generation
The system SHALL build a material context assembly for every live answer and screenshot answer before calling the answer model. The assembly MUST be derived only from the current confirmed session material snapshot and MUST separate fixed Resume/JD context from Knowledge RAG context.

#### Scenario: Session has confirmed resume and JD
- **WHEN** a user asks a live interview question in a session with confirmed ready Resume and JD versions
- **THEN** the answer service loads those versions as fixed material context before model generation and records them in the answer provenance

#### Scenario: Session has confirmed knowledge materials
- **WHEN** a user asks a live interview question in a session with confirmed ready Knowledge versions
- **THEN** the retrieval service searches only those confirmed Knowledge versions and returns reranked chunks for the material context assembly

#### Scenario: Session has no confirmed materials
- **WHEN** a user asks a live interview question in a session with an explicitly confirmed empty material list
- **THEN** the answer service generates without personal material context and records that no personal source was used

### Requirement: Resume and JD are fixed prompt context, not RAG-only sources
The system SHALL treat Resume and JD as fixed session context for answer generation, while Knowledge materials SHALL be the only default RAG retrieval sources. A zero RAG chunk count MUST NOT be interpreted as Resume or JD being unused when fixed context was loaded.

#### Scenario: Answer uses resume without knowledge retrieval
- **WHEN** a user asks a question about their experience in a session with a confirmed Resume and no Knowledge materials
- **THEN** the answer may have zero retrieved chunks but MUST record the Resume as fixed context used for generation

#### Scenario: Knowledge retrieval is used alongside fixed context
- **WHEN** a user asks a question in a session with confirmed Resume, JD and Knowledge materials
- **THEN** the answer service combines fixed Resume/JD context with retrieved Knowledge context without searching unconfirmed library materials

### Requirement: Answers expose safe material provenance
The system SHALL return safe answer provenance that identifies which confirmed material sources were used, including source type, display name, document version, context role, retrieval counts and truncation indicators, without exposing full document text or internal prompts.

#### Scenario: Fixed materials are used
- **WHEN** an answer is generated with Resume or JD fixed context
- **THEN** the answer payload includes safe provenance entries for those materials with context role `fixed`

#### Scenario: Retrieved knowledge chunks are used
- **WHEN** an answer is generated with Knowledge RAG chunks
- **THEN** the answer payload includes safe provenance entries for the Knowledge sources with context role `retrieved` and safe score/count metadata

#### Scenario: Context is truncated
- **WHEN** fixed or retrieved context is truncated before model generation
- **THEN** the answer payload marks the corresponding source as truncated without exposing omitted content

### Requirement: Unavailable selected materials do not silently degrade to generic answers
The system SHALL detect when confirmed materials cannot be loaded, parsed, retrieved or injected into the answer context and MUST surface a safe unavailable-source reason in the answer task or error response. The system MUST NOT silently ignore selected materials and produce an answer that appears grounded in them.

#### Scenario: Confirmed resume markdown is missing
- **WHEN** a session has a confirmed Resume but the processed Markdown cannot be read at answer time
- **THEN** the answer task reports the Resume as unavailable and does not claim to have used that Resume

#### Scenario: Confirmed knowledge retrieval returns no relevant chunks
- **WHEN** Knowledge materials are confirmed but retrieval finds no relevant chunks for the question
- **THEN** the generated answer states that no matching knowledge material was used and MUST NOT invent candidate-specific facts

#### Scenario: Confirmed source was deleted after selection
- **WHEN** a confirmed material source is deleted before a future answer request
- **THEN** the source is excluded from model context and the answer provenance includes a deleted or unavailable marker

### Requirement: Prompt behavior prioritizes grounded user material
The answer prompt SHALL instruct the model to prioritize confirmed Resume, JD and retrieved Knowledge facts over general knowledge for candidate-specific claims, and SHALL prohibit inventing company names, project metrics, responsibilities or skills that are not present in the material context or user question.

#### Scenario: User asks about candidate project details
- **WHEN** the material context contains relevant project details from the user's Resume or Knowledge materials
- **THEN** the answer grounds candidate-specific claims in those details rather than producing generic examples

#### Scenario: User asks for details absent from materials
- **WHEN** the confirmed materials do not contain the requested candidate-specific details
- **THEN** the answer states the limitation and suggests a safe way to answer without fabricating facts

### Requirement: Grounding behavior is testable end to end
The system SHALL include tests or eval cases that verify material upload or selection, session confirmation, answer generation, material provenance and no-fabrication behavior for Resume, JD and Knowledge materials.

#### Scenario: Resume-grounded answer test
- **WHEN** a synthetic Resume with a unique project fact is confirmed for a session and the user asks about experience
- **THEN** the generated or evaluated answer includes that fact and records the Resume in provenance

#### Scenario: Knowledge-grounded answer test
- **WHEN** a synthetic Knowledge document with a unique domain fact is confirmed for a session and the user asks a related question
- **THEN** retrieval returns a matching chunk and the answer provenance records the Knowledge source

#### Scenario: No-context answer test
- **WHEN** no materials are confirmed and the user asks for candidate-specific experience
- **THEN** the answer does not fabricate a resume-like history and records that no personal material was used
