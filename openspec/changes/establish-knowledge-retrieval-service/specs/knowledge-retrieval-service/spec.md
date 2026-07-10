## ADDED Requirements

### Requirement: The system MUST provide one unified knowledge retrieval service for interview context
The system SHALL provide a single Knowledge Retrieval Service that accepts a user question plus interview-related context and returns structured knowledge context for downstream AI services.

#### Scenario: Unified retrieval entrypoint
- **WHEN** an authorized service submits a user question with interview context
- **THEN** the system MUST invoke one retrieval service entrypoint rather than querying Resume, JD, and Knowledge Base through separate application-level retrieval flows

#### Scenario: Retrieval remains decoupled from chat generation
- **WHEN** retrieval completes successfully
- **THEN** the service MUST return structured context rather than directly calling an LLM or generating a final answer

### Requirement: The retrieval service MUST support joint retrieval across Resume, JD, and Knowledge Base
The system SHALL support combined retrieval across Resume, JD, and Knowledge Base vector sources so that one question can retrieve context from all approved interview materials.

#### Scenario: Joint multi-source recall
- **WHEN** a question is searched against the user’s approved interview materials
- **THEN** the system MUST be able to return relevant context from Resume, JD, and Knowledge Base in one retrieval result

#### Scenario: Source metadata remains visible
- **WHEN** recalled context is returned
- **THEN** each recalled item MUST preserve source metadata so downstream services can distinguish whether it came from Resume, JD, or Knowledge Base

### Requirement: The retrieval service MUST execute the defined retrieval stages
The system SHALL process retrieval requests through query embedding, vector search, metadata filtering, TopK recall, reranking, and context building stages.

#### Scenario: Ordered retrieval pipeline
- **WHEN** a retrieval request succeeds
- **THEN** it MUST progress through Query Embedding, pgvector similarity search, metadata filtering, TopK recall, reranking, and context building before returning context

#### Scenario: Context comes from filtered recalled chunks
- **WHEN** the final context is returned
- **THEN** it MUST be built from recalled and filtered chunk records rather than directly from raw vector rows without context construction

### Requirement: The retrieval service MUST support metadata filtering
The system SHALL support metadata-based filtering so retrieval can be scoped to the correct user, interview session, document types, collections, or other approved material boundaries.

#### Scenario: Filter by selected context scope
- **WHEN** an interview request specifies a subset of approved materials
- **THEN** the retrieval service MUST restrict vector recall to chunks whose metadata matches that scope

#### Scenario: Filter prevents cross-user leakage
- **WHEN** vector search is executed
- **THEN** the retrieval service MUST apply metadata filters that prevent recall from another user’s stored materials

### Requirement: The retrieval service MUST support configurable TopK and retrieval strategies
The system SHALL support configurable candidate recall counts, final returned counts, and retrieval strategies without changing API handler code.

#### Scenario: Candidate and final TopK differ
- **WHEN** a retrieval request uses reranking
- **THEN** the service MUST be able to recall a larger candidate set before returning a smaller final TopK result

#### Scenario: Retrieval strategy changes through configuration
- **WHEN** deployment configuration changes the retrieval strategy or TopK values
- **THEN** the retrieval service MUST apply those settings through runtime configuration rather than hard-coded constants

### Requirement: The retrieval service MUST support pluggable reranking
The system SHALL support a reranking layer that can reorder recalled candidates before context building and can be enabled, disabled, or replaced without changing retrieval orchestration.

#### Scenario: Reranker reorders recalled candidates
- **WHEN** reranking is enabled
- **THEN** the retrieval service MUST be able to reorder candidate chunks before building the final context

#### Scenario: Retrieval still works when reranker is disabled
- **WHEN** reranking is disabled by configuration
- **THEN** the retrieval service MUST still return filtered TopK context using the base recall ordering

### Requirement: The retrieval service MUST expose a retrieval API and structured context output
The system SHALL provide an API that returns retrieval results in a structured form suitable for downstream Chat Service consumption.

#### Scenario: Retrieval API returns structured result
- **WHEN** a client or internal service requests retrieval for a question
- **THEN** the API MUST return recalled items, source metadata, ranking information, and a context payload ready for downstream use

#### Scenario: Retrieval output is reusable by chat
- **WHEN** Chat Service consumes retrieval output
- **THEN** it MUST be able to use the returned context without requiring the retrieval layer to also build prompts or invoke a language model

### Requirement: The retrieval service MUST produce structured logs without exposing sensitive content
The system SHALL emit retrieval logs and events that are operationally useful while excluding full user questions, full recalled documents, or oversized context payloads from ordinary logs.

#### Scenario: Retrieval observability
- **WHEN** a retrieval request starts, succeeds, or fails
- **THEN** the system MUST log structured metadata such as request id, session id, filter scope, candidate count, final count, provider name, duration, and error code

#### Scenario: Sensitive retrieval content is excluded from logs
- **WHEN** retrieval logs are recorded
- **THEN** they MUST NOT include full question text, full recalled chunk bodies, or full assembled context text in ordinary logs
