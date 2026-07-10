## ADDED Requirements

### Requirement: All parsed Markdown documents MUST enter one unified embedding pipeline
The system SHALL route Resume, JD, and Knowledge Base Markdown documents produced by the parser service into one shared Embedding Pipeline rather than embedding chunking or vector-writing logic inside the parser or upload services.

#### Scenario: Shared embedding entrypoint
- **WHEN** a Resume, JD, or Knowledge Base document has completed parsing into normalized Markdown
- **THEN** the system MUST invoke the same Embedding Pipeline entrypoint with Markdown content and document metadata

#### Scenario: Parser and embedding remain decoupled
- **WHEN** the Embedding Pipeline is executed
- **THEN** it MUST consume parser output Markdown instead of re-reading or re-parsing the original binary document

### Requirement: The embedding pipeline MUST process Markdown through ordered post-parse stages
The system SHALL execute Markdown documents through ordered stages that cover cleaning, chunk splitting, metadata construction, embedding generation, vector persistence, and status update.

#### Scenario: Ordered embedding stages
- **WHEN** an embedding task runs successfully
- **THEN** it MUST progress through Document Cleaner, Chunk Splitter, Chunk Metadata Builder, Embedding Model, pgvector storage, and processing status update in that order

#### Scenario: Downstream vector data comes from cleaned chunks
- **WHEN** vector records are written for a document
- **THEN** those vectors MUST be derived from cleaned Markdown chunks rather than directly from raw parser output without chunk preparation

### Requirement: The embedding pipeline MUST support document-type-specific chunk strategies
The system SHALL allow Resume, JD, and Knowledge Base documents to share one pipeline while using different chunk configuration profiles when needed.

#### Scenario: Resume and JD can use different chunk settings
- **WHEN** two different document types are processed
- **THEN** the pipeline MUST be able to apply different chunk size, overlap, or splitting rules without creating separate pipeline implementations

#### Scenario: Chunk configuration is runtime-managed
- **WHEN** deployment or product settings change chunk parameters
- **THEN** the pipeline MUST apply those chunk settings through configuration rather than hard-coded request-handler logic

### Requirement: The embedding pipeline MUST support configurable embedding models and batch processing
The system SHALL support pluggable embedding models and batch-oriented vector generation so that multiple chunks can be embedded efficiently within one task.

#### Scenario: Batch embedding execution
- **WHEN** a document produces multiple chunks
- **THEN** the embedding pipeline MUST be able to send chunks to the embedding model in batches rather than requiring one request per chunk only

#### Scenario: Embedding model is replaceable
- **WHEN** the deployment switches to a different embedding provider or model
- **THEN** the pipeline MUST use the new model through a replaceable embedding service boundary instead of changing pipeline orchestration behavior

### Requirement: The embedding pipeline MUST persist vectors with chunk metadata in pgvector
The system SHALL write chunk embeddings and their metadata to pgvector storage so that later retrieval systems have one consistent vector source.

#### Scenario: Successful vector persistence
- **WHEN** embedding generation completes successfully
- **THEN** the pipeline MUST write vectors together with chunk metadata, document identity, and model/version information into vector storage

#### Scenario: Metadata remains available for retrieval filtering
- **WHEN** a vector record is stored
- **THEN** it MUST preserve metadata sufficient for later document-level or type-level filtering without requiring re-parsing

### Requirement: The embedding pipeline MUST expose embedding-stage status and retry behavior
The system SHALL track embedding-stage execution states, distinguish retryable failures, and support task retry without requiring the user to re-upload documents.

#### Scenario: Embedding stage progression
- **WHEN** an embedding task proceeds normally
- **THEN** the system MUST expose stage progression for chunking, embedding, vector writing, and completion

#### Scenario: Retryable embedding failure
- **WHEN** the embedding model or vector storage fails due to a recoverable backend issue
- **THEN** the system MUST mark the failure as retryable and allow the task to be retried automatically or manually

### Requirement: The embedding pipeline MUST support vector rebuild for existing documents
The system SHALL allow an existing parsed document to rebuild its chunks and vectors when chunk strategy, model choice, or stored vectors need to be refreshed.

#### Scenario: Manual vector rebuild
- **WHEN** an authorized system action requests vector rebuild for an existing document
- **THEN** the system MUST allow a new embedding task to run without requiring a fresh document upload

#### Scenario: Rebuild preserves version distinction
- **WHEN** vectors are rebuilt for an existing document
- **THEN** the system MUST preserve enough version or rebuild metadata to distinguish the new vector set from the previous one

### Requirement: The embedding pipeline MUST produce structured logs without leaking content
The system SHALL emit structured embedding-pipeline logs and events that are operationally useful while excluding raw Markdown, chunk body text, and embedding vector values from ordinary logs.

#### Scenario: Embedding observability
- **WHEN** an embedding task starts, succeeds, retries, or fails
- **THEN** the system MUST log structured metadata such as task id, document id, chunk count, model, batch size, duration, and error code

#### Scenario: Sensitive content is excluded from logs
- **WHEN** embedding logs or task events are recorded
- **THEN** they MUST NOT include full Markdown text, chunk body text, or embedding vectors
