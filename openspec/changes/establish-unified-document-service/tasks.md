## 1. Shared contracts and data model

- [x] 1.1 Define unified document protocol types for document kind, validation rules, lifecycle status, list items, delete commands, and processing handoff metadata
- [x] 1.2 Design PostgreSQL document metadata schema and migration placeholders for ownership, object keys, file attributes, lifecycle state, and deletion markers
- [x] 1.3 Consolidate file-format and file-size validation rules so Resume, JD, and Knowledge uploads share one authoritative definition

## 2. Backend document service foundation

- [x] 2.1 Implement a unified Document Service in `apps/backend` that creates upload intents, completes uploads, registers metadata, and enforces permission boundaries
- [x] 2.2 Add OSS object-key naming rules and storage integration for unique document persistence without filename collisions
- [x] 2.3 Add document list, document detail, and document delete APIs with unified response envelopes and authorization checks
- [x] 2.4 Add processing-handoff fields or service boundaries so later pipelines can claim uploaded documents without embedding parsing or RAG logic

## 3. Module integration and frontend alignment

- [x] 3.1 Refactor Resume, JD, and Knowledge upload routes to reuse the unified Document Service while preserving approved product interactions
- [x] 3.2 Update the web material management layer to call the unified document APIs for upload status, list refresh, and deletion
- [x] 3.3 Surface consistent format, size, and status guidance in the material library UI for Resume, JD, and Knowledge documents

## 4. Verification and documentation

- [x] 4.1 Add backend tests for format validation, size validation, unique naming, metadata registration, listing, deletion, and permission rejection
- [x] 4.2 Update architecture and engineering docs to describe the Document Service boundary and its separation from the future Document Processing Pipeline
- [x] 4.3 Run `openspec validate establish-unified-document-service --strict` and record the verification commands used for the implementation
