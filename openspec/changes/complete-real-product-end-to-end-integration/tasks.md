## 1. Frontend real-data integration mode

- [x] 1.1 Audit the current frontend data-loading path and identify every core view that still falls back to fixture or mock state
- [x] 1.2 Add an API-only integration mode that fails on missing backend data instead of silently falling back to fixture state
- [ ] 1.3 Wire interview list, materials, billing state, session state, and history views to real backend API responses while preserving approved prototype interactions

## 2. Backend fact-source hardening for integration

- [x] 2.1 Audit current `InMemory*`, `Synthetic*`, and placeholder adapters across authentication, documents, session, chat, screenshot, speech, and retrieval flows
- [ ] 2.2 Replace or isolate the adapters that block real end-to-end conclusions for login, materials, session, history, and retrieval state
- [ ] 2.3 Ensure OSS, MinerU, Embedding, pgvector, Retrieval, Chat, Screenshot, and Speech flows use configured real providers in integration mode

## 3. Real end-to-end scenario execution

- [ ] 3.1 Implement real login, Resume upload, JD upload, and Knowledge upload integration scenarios
- [ ] 3.2 Implement real document-processing scenarios covering OSS, MinerU, Embedding, and pgvector-backed persistence
- [ ] 3.3 Implement retrieval-backed Interview Session, Chat, Screenshot, Speech, and History integration scenarios

## 4. Reporting and triage outputs

- [x] 4.1 Extend the integration runner to output Integration Report for the full real product flow
- [x] 4.2 Generate a structured Bug List with severity, attribution, reproduction context, and expected vs observed behavior
- [x] 4.3 Generate a structured TODO List for deferred adapter replacements, hardening work, and non-blocking follow-ups

## 5. Validation and documentation

- [x] 5.1 Add or update regression tests and AI evals required by the real integration path
- [x] 5.2 Document real integration environment setup, frontend API-only mode, execution commands, and troubleshooting guidance
- [x] 5.3 Validate the change with `openspec validate complete-real-product-end-to-end-integration --strict`
