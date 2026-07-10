## 1. Diagnose Current Material Grounding Gap

- [ ] 1.1 Add a targeted reproduction script or test that creates a session, confirms Resume/JD/Knowledge materials, asks a question and records fixed-context count, RAG count and provenance
- [x] 1.2 Inspect current Chat Service and Screenshot Answer Service material loading paths and identify where confirmed Resume/JD/Knowledge can be dropped silently
- [x] 1.3 Confirm current frontend displays enough information to distinguish fixed Resume/JD usage from Knowledge RAG usage

## 2. Protocol and Data Shape

- [x] 2.1 Extend answer task protocol with material context assembly status, fixed source count, retrieved source count and unavailable source summaries
- [x] 2.2 Extend provenance protocol to include source kind, document ID, version ID, context role `fixed` or `retrieved`, truncation status and safe evidence summary
- [x] 2.3 Ensure protocol types do not expose raw document text, full prompts, embeddings, OSS signed URLs or provider payloads

## 3. Backend Material Context Assembly

- [ ] 3.1 Implement a reusable material context assembly service for live answers and screenshot answers
- [x] 3.2 Load confirmed Resume and JD processed Markdown as fixed context with safe truncation and source metadata
- [x] 3.3 Retrieve confirmed Knowledge documents only through the existing RAG boundary with query embedding, vector search and rerank
- [x] 3.4 Record unavailable selected sources with safe reason codes when processed artifacts, document versions or vector chunks are missing
- [x] 3.5 Prevent selected but unavailable materials from being silently ignored in answer generation

## 4. Prompt and Answer Generation

- [x] 4.1 Update live answer prompt templates to distinguish fixed Resume/JD context from retrieved Knowledge context
- [x] 4.2 Update screenshot answer prompt templates to share the same material context rules
- [x] 4.3 Add no-fabrication instructions for absent candidate-specific facts, companies, projects, metrics and skills
- [x] 4.4 Persist and return safe material provenance on completed, degraded and no-context answers

## 5. Web Experience

- [ ] 5.1 Keep the existing preparation page layout while showing backend selectable status and unavailable reasons for materials
- [x] 5.2 Update live answer source display so Resume/JD fixed context usage is visible even when RAG chunk count is zero
- [x] 5.3 Show a clear warning when a selected material becomes unavailable and the answer did not use it
- [ ] 5.4 Ensure stale, deleted or failed selected sources require reconfirmation instead of silent replacement

## 6. Tests and Evals

- [ ] 6.1 Add backend tests for Resume-only, JD-only, Knowledge-only and combined material answering provenance
- [ ] 6.2 Add regression tests for selected material missing processed Markdown or vector chunks
- [ ] 6.3 Add Web tests for selectable state, unavailable warnings and fixed-source provenance display
- [x] 6.4 Add AI eval cases for grounded Resume/JD answers, grounded Knowledge answers and no-context no-fabrication behavior

## 7. Integration Verification

- [ ] 7.1 Run targeted local end-to-end verification using synthetic materials through upload, processing, session confirmation and live answer
- [ ] 7.2 Run targeted real-provider verification with local `.env` configuration when OSS, database, embedding, rerank and chat providers are available
- [x] 7.3 Validate the OpenSpec change with `openspec validate fix-material-grounded-interview-answers --strict`
- [x] 7.4 Document the expected interpretation: Resume/JD usage appears as fixed material provenance; Knowledge usage appears as RAG retrieval provenance

## 8. Session Material Binding Persistence

- [x] 8.1 Ensure preparation-page material confirmation calls the backend session material confirmation API instead of only updating browser state
- [x] 8.2 Persist interview sessions, confirmed material bindings, context entries and usage records in PostgreSQL when database configuration is available
- [x] 8.3 Add migration DDL for persistent interview session tables
