## 1. Contracts and Configuration

- [x] 1.1 Extend protocol types for persisted material documents, document versions, upload intents, processing jobs, index jobs, vector source metadata and session material snapshots
- [x] 1.2 Add backend configuration fields for OSS key prefix, environment label, upload TTL, document size limits, parser, embedding, rerank and pgvector runtime settings
- [x] 1.3 Document required `.env` / `.env.local` values for OSS, PostgreSQL, pgvector, parser, embedding, rerank and chat providers without exposing secrets to the Web client
- [x] 1.4 Add sensitive-field redaction tests for material metadata, object keys, provider payloads, prompts and environment secrets

## 2. Database and OSS Persistence

- [x] 2.1 Add PostgreSQL migrations for documents, document_versions, upload_intents, processing_jobs, document_chunks, index_jobs, session_material_snapshots and deletion_jobs
- [x] 2.2 Implement repository methods for owner-scoped create, list, read, replace, disable, soft-delete and status transitions
- [x] 2.3 Implement the approved OSS object-key generator for original files, processed artifacts, deletion markers, temporary uploads and exports
- [x] 2.4 Connect upload intent creation and completion to real OSS object metadata verification and PostgreSQL records
- [x] 2.5 Add idempotency and content-fingerprint handling for repeated upload completion and unchanged content reuse
- [x] 2.6 Add asynchronous deletion scheduling for raw OSS objects, processed artifacts and vector rows while preserving minimal audit metadata

## 3. Document Processing and Indexing

- [x] 3.1 Implement durable processing job orchestration for parsing, Markdown normalization, chunking, embedding and pgvector indexing
- [x] 3.2 Connect PDF, DOCX, DOC, TXT and MD parsing through the existing parser adapter boundary with safe failure codes
- [x] 3.3 Persist normalized Markdown and chunk manifests under the approved processed OSS path
- [x] 3.4 Write chunk embeddings to pgvector with user, document, version, kind, collection and embedding model metadata
- [ ] 3.5 Implement retry, timeout, cancellation and worker-resume behavior without duplicate vector rows or duplicate settled usage
- [ ] 3.6 Add tests for unsupported files, oversized files, no-text files, parser failure, embedding failure, worker retry and duplicate content reuse

## 4. Indexing Metering

- [x] 4.1 Connect knowledge indexing quotes to parsed token estimates, catalog version, tokenizer version and projected balance
- [x] 4.2 Reserve points or long-pass knowledge allowance only after explicit confirmation
- [x] 4.3 Settle points or allowance exactly once after usable pgvector index delivery
- [x] 4.4 Release reservations on parse, embedding, pgvector, timeout or cancellation failure
- [ ] 4.5 Add concurrency tests for quote replay, duplicate workers, unchanged content and insufficient balance recovery

## 5. RAG Retrieval and Answer Grounding

- [x] 5.1 Implement retrieval filters that require user ID and confirmed session document version allowlist
- [x] 5.2 Add rerank and context assembly that returns structured safe context with source labels, versions, scores and truncation metadata
- [x] 5.3 Connect live manual answer, interviewer-triggered answer and screenshot answer generation to the same session RAG context boundary
- [x] 5.4 Ensure answers with no relevant material state that no personal source was used and do not fabricate candidate-specific details
- [x] 5.5 Add AI prompt and eval cases for grounded answers, no-context answers, deleted-source answers and sensitive-content exclusion
- [x] 5.6 Add retrieval logs and metrics that exclude raw document text, screenshots, full prompts, embeddings and provider payloads

## 6. Web and Session Integration

- [x] 6.1 Update `/api/v1/web/state` and material APIs to return persisted documents, versions, processing/index status, deletion markers and supported upload limits
- [ ] 6.2 Keep the existing library page layout while wiring create, upload, retry, replace, rename, disable and delete actions to persisted backend state
- [x] 6.3 Update preparation page adapters so only indexed ready non-deleted non-disabled versions can be selected
- [x] 6.4 Save immutable session material snapshots with source ID, document version ID, display name, kind, index state, selection revision and confirmation time
- [x] 6.5 Show stale/deleted selected material attention states without silently replacing sources
- [ ] 6.6 Add Web tests for material list rendering, processing states, disabled selection, deletion invalidation and snapshot confirmation

## 7. Integration and Operations

- [x] 7.1 Add OSS/PostgreSQL/pgvector integration checks for upload, metadata persistence, processed artifacts and vector rows using synthetic documents
- [x] 7.2 Add end-to-end scenario from upload through parse, index, session selection, live answer and answer provenance
- [x] 7.3 Add cleanup verification for deleted documents, deleted collections, historical source tombstones and future retrieval exclusion
- [x] 7.4 Update docs for commercial material storage, OSS object paths, database tables, RAG flow and local environment setup
- [x] 7.5 Run OpenSpec strict validation for this change
- [ ] 7.6 Run backend tests, Web typecheck/tests and targeted end-to-end integration with real OSS/database configuration from the local environment
