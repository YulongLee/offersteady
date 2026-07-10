## 1. Current State Diagnosis

- [ ] 1.1 Map the current upload, MinerU, Markdown artifact, chunk, embedding, vector and selectable-state flow for Resume, JD and Knowledge materials
- [ ] 1.2 Identify every synchronous OSS, parser or vector check currently executed during preparation-page material confirmation
- [ ] 1.3 Record the current session persistence behavior for interview sessions, material bindings, context entries and answer tasks
- [ ] 1.4 Create a targeted reproduction script for upload-ready material, interview creation, material confirmation and answer provenance

## 2. Material Capability State Model

- [ ] 2.1 Extend protocol types with material artifact verification, selectable state and safe unavailable reason fields
- [ ] 2.2 Extend backend document records or version records to persist processed Markdown, chunks and vector readiness metadata
- [ ] 2.3 Extend backend document records or version records with OSS/database sync status and last verified timestamp
- [ ] 2.4 Ensure library and preparation API payloads expose the same document ID, version ID, kind, status, sync status, index state, selectable flag and safe reason
- [ ] 2.5 Update material object key helpers or documentation to make original, normalized Markdown and chunks paths deterministic by user, document and version

## 3. Backend Processing Pipeline

- [ ] 3.1 Ensure upload completion creates a processing job and returns control without requiring the user to keep the upload modal open
- [ ] 3.2 Ensure MinerU conversion stores verified normalized Markdown for PDF, DOCX, DOC, TXT and MD inputs
- [ ] 3.3 Ensure Knowledge materials generate chunks.jsonl, embeddings and runtime vector records before becoming selectable
- [ ] 3.4 Ensure Resume and JD materials become selectable after normalized Markdown is verified without requiring default RAG retrieval
- [ ] 3.5 Persist safe processing failures and retryable states without exposing raw provider payloads or document text
- [ ] 3.6 Ensure upload completion verifies the OSS original object before creating a ready processing record

## 4. Material Synchronization and Deletion

- [ ] 4.1 Ensure frontend material lists are loaded only from backend API state, not OSS listing or browser-only state
- [ ] 4.2 Implement backend reconciliation for database records whose required OSS artifacts are missing
- [ ] 4.3 Ensure deleting a material immediately marks it deleted and unselectable in the database
- [ ] 4.4 Ensure material deletion schedules cleanup of original OSS objects, processed OSS artifacts and vector chunks
- [ ] 4.5 Ensure failed OSS/vector cleanup remains retryable without re-exposing the material as selectable

## 5. Lightweight Interview Material Binding

- [ ] 5.1 Change session material confirmation to validate ownership, kind, current version, status, sync status and selectable state from the database only
- [ ] 5.2 Remove synchronous MinerU, embedding rebuild, broad OSS scan or artifact generation from the confirmation request path
- [ ] 5.3 Persist confirmed session material snapshots by document version and restore them after backend restart
- [ ] 5.4 Mark stale, deleted or unselectable previously selected materials as attention-required when reopening preparation
- [ ] 5.5 Ensure starting an interview is blocked until the backend-confirmed material selection is saved, including confirmed empty selection

## 6. Answer Material Assembly and Grounding

- [ ] 6.1 Implement or consolidate a reusable material context assembly service for live and screenshot answers
- [ ] 6.2 Load confirmed Resume and JD Markdown as fixed Prompt context with safe truncation and provenance
- [ ] 6.3 Retrieve only confirmed Knowledge document versions through embedding search and rerank
- [ ] 6.4 Record unavailable selected sources when Markdown, chunks or vector records are missing at answer time
- [ ] 6.5 Update prompts so candidate-specific claims prioritize confirmed material context and avoid fabricated experiences

## 7. Web Experience

- [ ] 7.1 Update library page status labels to show processing, indexing, ready, failed, stale, sync mismatch and unselectable reasons consistently
- [ ] 7.2 Update preparation page confirmation to show backend saving state and avoid blocking on heavy material processing
- [ ] 7.3 Replace ambiguous “个人资料” wording with “已选资料” or “资料库内容” where the source can include Knowledge materials
- [ ] 7.4 Update answer cards to show fixed source count, retrieved Knowledge count, unavailable sources and no-selected-material state
- [ ] 7.5 Keep the existing prototype layout and navigation structure while improving status and grounding clarity

## 8. Tests, Evals and Verification

- [ ] 8.1 Add backend tests for selectable-state derivation for Resume, JD and Knowledge materials
- [ ] 8.2 Add backend tests proving material confirmation does not invoke MinerU, embedding rebuild or broad OSS scans
- [ ] 8.3 Add backend tests for session snapshot persistence and restore after repository reinitialization
- [ ] 8.4 Add backend tests for OSS/database mismatch reconciliation and deletion cleanup jobs
- [ ] 8.5 Add answer assembly tests for Resume-only, JD-only, Knowledge-only and combined materials
- [ ] 8.6 Add regression tests for selected materials missing Markdown, chunks or vector records at answer time
- [ ] 8.7 Add Web tests for preparation selectable states, backend confirmation pending state and unavailable warnings
- [ ] 8.8 Add AI eval cases for grounded Resume/JD answers, grounded Knowledge answers, unavailable material degradation and no-context no-fabrication
- [ ] 8.9 Run OpenSpec strict validation for this change and record any implementation validation commands that are actually executed

## 9. Migration and Cleanup

- [ ] 9.1 Backfill or reconcile existing material records so ready/indexed documents expose correct selectable and sync state
- [ ] 9.2 Ensure existing OSS artifacts are not deleted or moved during migration without an explicit deletion job
- [ ] 9.3 Remove or isolate obsolete frontend-only material selection state that can diverge from backend session snapshots
- [ ] 9.4 Document the final material, OSS/database synchronization and interview workflow in docs for future development handoff

## 12. Commercial Architecture Hardening

- [ ] 12.1 Introduce or document a Worker/Queue boundary so API requests only enqueue long-running material processing, deletion and reconciliation work
- [ ] 12.2 Add persistent material artifact manifest records for original files, normalized Markdown, chunk manifests and deletion markers
- [ ] 12.3 Add durable processing job records with stage, status, retry count, safe error code and timestamps
- [ ] 12.4 Add durable deletion job records for OSS artifact cleanup and vector chunk cleanup
- [ ] 12.5 Add safe AI usage records for MinerU, qwen3-vl, embedding, rerank and chat operations
- [ ] 12.6 Add RAG retrieval trace records that identify filters, counts and source versions without storing sensitive full text
- [ ] 12.7 Keep qwen3-vl screenshot recognition separate from Chat answer generation in backend adapters and prompts
- [ ] 12.8 Add commercial-readiness tests for user isolation across DB, OSS object keys, session material binding and RAG filters
