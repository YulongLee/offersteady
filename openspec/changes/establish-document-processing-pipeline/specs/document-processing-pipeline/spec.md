## ADDED Requirements

### Requirement: All uploaded documents must enter one asynchronous processing pipeline
The system SHALL route every uploaded Resume, JD, and Knowledge Base document through one shared asynchronous Document Processing Pipeline after the upload lifecycle is completed by the Document Service.

#### Scenario: Upload returns before processing completes
- **WHEN** a client successfully completes a document upload
- **THEN** the upload API MUST return success immediately without waiting for parsing, chunking, embedding, or vector storage to finish

#### Scenario: Shared pipeline across document types
- **WHEN** the uploaded document type is Resume, JD, or Knowledge Base
- **THEN** the system MUST create a processing task in the same pipeline framework rather than sending each type through a separate processing architecture

### Requirement: Processing tasks must execute through ordered asynchronous stages
The system SHALL execute document processing tasks through ordered asynchronous stages that cover parsing, normalization, chunking, embedding, vector persistence, and final status update.

#### Scenario: Ordered pipeline stages
- **WHEN** a processing task is executed successfully
- **THEN** it MUST progress through OSS retrieval, MinerU parsing, Markdown normalization, chunk splitting, embedding generation, pgvector persistence, and status completion in that logical order

#### Scenario: Extensible document type support
- **WHEN** a new document type is introduced in the future
- **THEN** the system MUST be able to register type-specific parsing or chunking behavior without creating a separate pipeline architecture

### Requirement: Processing tasks must expose stable execution states
The system SHALL maintain explicit processing task states so that clients and internal services can understand whether a document is waiting, in progress, completed, or failed.

#### Scenario: Successful state progression
- **WHEN** a processing task proceeds normally
- **THEN** its execution state MUST move through `UPLOADED`, `QUEUED`, `PARSING`, `CHUNKING`, `EMBEDDING`, and `COMPLETED`

#### Scenario: Failed task state
- **WHEN** a processing stage cannot complete and recovery is not immediately successful
- **THEN** the task MUST enter `FAILED` and preserve enough metadata for later diagnosis or retry

### Requirement: Failed tasks must support automatic and manual retry
The system SHALL support both automatic retry for recoverable failures and manual reprocessing for operator-initiated recovery.

#### Scenario: Automatic retry
- **WHEN** a processing task fails due to a recoverable backend or provider error
- **THEN** the system MUST retry automatically according to configured retry rules before marking the task as permanently failed

#### Scenario: Manual reprocessing
- **WHEN** an authorized operator or internal service requests a failed document to be reprocessed
- **THEN** the system MUST allow the document to re-enter the processing pipeline without requiring the end user to upload the file again

### Requirement: Processing status must be queryable through API
The system SHALL provide APIs that allow clients or internal services to query processing task state and document processing readiness.

#### Scenario: Query task status
- **WHEN** a client requests the processing status of a document or task
- **THEN** the API MUST return the current processing state, retry information if available, and whether the document is ready for downstream AI use

#### Scenario: Frontend prototype remains unchanged
- **WHEN** processing status APIs are introduced
- **THEN** the backend changes MUST NOT require a change to the approved prototype page structure or interaction order

### Requirement: Pipeline execution must be observable and configurable
The system SHALL provide structured logging and runtime configuration for parser, chunking, embedding, retry, and vector persistence behavior without exposing sensitive document contents in ordinary logs.

#### Scenario: Structured task logging
- **WHEN** a processing task enters or leaves a stage
- **THEN** the system MUST record structured task events including document identity, stage, retry count, timing, and error code without logging raw document body, chunk text, or embedding vectors

#### Scenario: Runtime configurable providers and thresholds
- **WHEN** deployment configuration changes parser endpoints, embedding providers, retry counts, or chunking thresholds
- **THEN** the pipeline MUST apply those values through runtime configuration rather than hard-coded constants in request handlers
