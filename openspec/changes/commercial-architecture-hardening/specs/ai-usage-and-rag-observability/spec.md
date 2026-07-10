## ADDED Requirements

### Requirement: AI provider usage is recorded safely
The system SHALL record safe usage records for parser, vision, embedding, rerank and chat operations. Usage records MUST include owner, provider, model, operation kind, related task or job, counts or units, and trace ID when available.

#### Scenario: Chat answer completes
- **WHEN** the Chat provider returns a live answer
- **THEN** the backend records a chat usage record linked to the answer task and session

#### Scenario: Screenshot recognition runs
- **WHEN** qwen3-vl is used to recognize a screenshot or photo question
- **THEN** the backend records a vision usage record separate from the final chat answer usage

#### Scenario: Embedding builds knowledge chunks
- **WHEN** the embedding provider processes Knowledge chunks
- **THEN** the backend records embedding usage linked to the processing job and document version

### Requirement: RAG retrieval traces are available without sensitive text
The system SHALL record safe RAG retrieval traces that identify query hash, owner, session, filter document versions, candidate count, reranked count, returned count and source IDs. The trace MUST NOT store raw resume text, JD text, full chunk text, full prompt or embeddings.

#### Scenario: Knowledge retrieval returns chunks
- **WHEN** a live answer retrieves Knowledge chunks
- **THEN** the backend records a RAG trace with counts and source version IDs

#### Scenario: Knowledge retrieval returns no chunks
- **WHEN** retrieval finds no relevant chunks for confirmed Knowledge materials
- **THEN** the trace records zero returned count and the answer provenance can explain that no matching knowledge material was used

### Requirement: Model responsibilities remain separated
The system SHALL keep MinerU parsing, qwen3-vl vision recognition, embedding, rerank and chat answer generation as separate backend adapter responsibilities.

#### Scenario: Screenshot answer is requested
- **WHEN** a user asks for a screenshot answer
- **THEN** qwen3-vl produces normalized visual question context before the Chat model generates the final answer
