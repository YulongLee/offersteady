## 1. Protocol and Data Model

- [x] 1.1 Add protocol types for material artifacts, artifact sync status, processing jobs, deletion jobs, AI usage records and RAG traces
- [x] 1.2 Add backend ports and dataclasses for artifact manifest records and durable job records
- [x] 1.3 Add PostgreSQL persistence for material artifacts, processing jobs, deletion jobs, AI usage records and RAG retrieval traces
- [x] 1.4 Add migration SQL for the new commercial hardening tables without deleting existing user material data

## 2. Job Orchestration Foundation

- [x] 2.1 Define a minimal JobPort abstraction for enqueue, claim, update, retry and complete operations
- [x] 2.2 Implement a PostgreSQL-backed job repository for processing and deletion jobs
- [x] 2.3 Add a worker service or CLI entrypoint that can run queued material jobs outside request handlers
- [x] 2.4 Add safe retry policy and max retry handling for transient provider, OSS and vector failures
- [x] 2.5 Ensure API endpoints enqueue jobs and return status without blocking on long-running material work

## 3. Material Artifact Manifest

- [x] 3.1 Write original upload artifact records when OSS upload completion is confirmed
- [x] 3.2 Write normalized Markdown artifact records when MinerU/normalization output is saved
- [x] 3.3 Write chunk manifest artifact records when chunks.jsonl is saved
- [x] 3.4 Derive material selectable state from required synced artifacts and vector readiness
- [x] 3.5 Expose artifact sync status and safe unavailable reasons through web state and material APIs

## 4. Deletion and Reconciliation

- [x] 4.1 Convert material deletion to DB tombstone plus durable deletion job
- [ ] 4.2 Ensure deletion jobs clean original OSS object, processed artifacts and vector chunks by document version
- [x] 4.3 Persist cleanup success or safe failure state without re-exposing deleted materials as selectable
- [ ] 4.4 Add reconciliation job logic for DB records whose required OSS artifacts are missing
- [x] 4.5 Add user-visible stale or missing-artifact states for reconciled mismatches

## 5. AI Usage and RAG Observability

- [x] 5.1 Add a safe usage recorder around MinerU parser calls
- [ ] 5.2 Add a safe usage recorder around qwen3-vl screenshot/photo recognition calls
- [ ] 5.3 Add safe usage records for embedding, rerank and chat model calls
- [x] 5.4 Add RAG retrieval trace records with query hash, filter version IDs, candidate counts, rerank counts and returned source IDs
- [x] 5.5 Ensure usage and trace records never store raw resume/JD text, screenshots, full prompts, embeddings or provider payloads

## 6. Model Adapter Boundaries

- [x] 6.1 Confirm qwen3-vl screenshot recognition is modeled as a Vision adapter separate from Chat answer generation
- [ ] 6.2 Route screenshot answers through vision recognition first, then the shared material-grounded answer assembly path
- [x] 6.3 Ensure model names, providers and credentials are resolved only on the backend
- [ ] 6.4 Update prompts and eval metadata to distinguish visual question context from grounded material context

## 7. Security Isolation

- [ ] 7.1 Add tests that users cannot confirm another user's document ID into their interview session
- [ ] 7.2 Add tests that arbitrary OSS object keys cannot be completed or loaded outside backend-issued intents
- [ ] 7.3 Add tests that RAG retrieval filters only confirmed session Knowledge document versions for the owner
- [ ] 7.4 Add tests that usage, trace and logs do not contain sensitive raw material text or provider payloads

## 8. Web and Product Feedback

- [x] 8.1 Update library state display to distinguish processing, synced, missing artifacts, failed and deleted states
- [x] 8.2 Update preparation page material eligibility to use backend selectable and sync status
- [x] 8.3 Update answer cards or debug summaries to show trace IDs and source counts safely when available
- [x] 8.4 Keep the current prototype layout and avoid introducing an admin dashboard in this change

## 9. Documentation and Verification

- [x] 9.1 Update docs with the final API/Worker/DB/OSS/AI architecture after implementation
- [x] 9.2 Add implementation notes for running the worker locally
- [x] 9.3 Run OpenSpec strict validation for this change
- [ ] 9.4 Run targeted backend tests for jobs, artifacts, deletion, usage, RAG trace and isolation
- [ ] 9.5 Run a local end-to-end smoke path: upload material, process via worker, confirm into interview, ask answer, inspect provenance and usage trace
