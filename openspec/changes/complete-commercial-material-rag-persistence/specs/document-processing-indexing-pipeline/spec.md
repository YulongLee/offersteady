## ADDED Requirements

### Requirement: Uploaded materials are processed into normalized indexed text
The system SHALL process uploaded material versions through parsing, Markdown normalization, chunking, embedding and pgvector indexing before they become eligible for interview selection or RAG retrieval.

#### Scenario: Document indexes successfully
- **WHEN** a supported uploaded document contains usable text and all processing stages complete
- **THEN** the system marks that document version as indexed and ready for future interview selection

#### Scenario: Document has no usable text
- **WHEN** parsing produces no usable text for indexing
- **THEN** the system marks the version failed, releases any reserved indexing charge and presents retry, replace or delete recovery

### Requirement: Processing and indexing jobs are durable and idempotent
The system SHALL persist processing and indexing jobs with idempotency keys, content fingerprints, provider versions, retry counts, status, safe error codes and timestamps so workers can resume without duplicate charges or duplicate vector rows.

#### Scenario: Worker retries after interruption
- **WHEN** a worker restarts after parsing or embedding was partially completed
- **THEN** it resumes from the persisted job state or replays idempotently without creating duplicate settled usage

#### Scenario: User uploads unchanged content again
- **WHEN** the same user submits unchanged content that already has a usable index
- **THEN** the system reuses the existing indexed result or usage record without charging again

### Requirement: pgvector entries preserve retrieval metadata
The system SHALL store vector chunks with user ID, document ID, version ID, document kind, collection ID when applicable, chunk ID, content hash, embedding model, embedding dimension and safe source summary metadata.

#### Scenario: Chunk is written to vector store
- **WHEN** embedding succeeds for a document chunk
- **THEN** the vector row includes enough metadata to filter by user, session material snapshot and document version during retrieval

### Requirement: Indexing metering settles only after usable index delivery
The system SHALL reserve points or a knowledge allowance only after explicit quote confirmation and SHALL settle exactly once only after a usable index is written and marked ready.

#### Scenario: Indexing fails after reservation
- **WHEN** parsing, embedding or pgvector storage fails before a usable index is delivered
- **THEN** the system releases the full reservation and keeps the uploaded document in a non-indexed recoverable state

#### Scenario: Indexing succeeds
- **WHEN** pgvector rows are committed and the document version is marked indexed
- **THEN** the system settles the reserved points or allowance exactly once for that document version
