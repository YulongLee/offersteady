## 1. Foundation Planning Alignment

- [x] 1.1 Reconcile this phase-one foundation change with the approved prototype flow and `define-mvp-technical-architecture` boundaries
- [x] 1.2 Document the target app/module ownership for `apps/web`, FastAPI backend, shared contracts, AI assets, and deferred desktop integration before code migration begins

## 2. FastAPI Backend Scaffold

- [x] 2.1 Decide whether the FastAPI foundation will replace the current `apps/api` prototype directory or be introduced as a new backend app with a clear migration note
- [x] 2.2 Create a runnable FastAPI application skeleton with app entry, versioned API root, health check, centralized config, and common exception handling
- [x] 2.3 Add feature-domain router placeholders for identity/session, resume, job description, knowledge/RAG, live answer, screenshot answer, billing, and system modules
- [x] 2.4 Implement uniform placeholder responses or not-implemented error models for reserved endpoints without adding real business logic
- [x] 2.5 Add backend tests for startup, health routes, versioned routing, and placeholder endpoint behavior

## 3. React Communication Foundation

- [x] 3.1 Introduce a frontend communication abstraction that keeps existing page structure and interaction behavior unchanged
- [x] 3.2 Add environment-based API configuration, request helpers, and normalized error handling for backend and fixture modes
- [x] 3.3 Refactor current fixture-backed data access behind replaceable adapters or repositories without rewriting page-level product flows
- [x] 3.4 Add frontend tests proving the current pending, empty, success, and error interaction states remain available during the backend transition

## 4. Shared Contracts and Feature Scaffolding

- [x] 4.1 Define shared DTO or contract locations for resume, JD, knowledge/RAG, live answer, screenshot answer, and session placeholder interactions
- [x] 4.2 Reserve explicit extension points for future file storage, parsing, retrieval, answer generation, screenshot analysis, and streaming adapters without connecting real providers
- [x] 4.3 Document how existing TypeScript prototype service logic is retained as reference only or migrated into shared contract/test coverage

## 5. Developer Experience and Verification

- [x] 5.1 Add or update developer run instructions for the React app, FastAPI app, and any combined local workflow introduced in this phase
- [x] 5.2 Validate the new foundation with typechecks, frontend tests, backend tests, and any contract checks introduced by the scaffold
- [x] 5.3 Run `openspec validate implement-mvp-phase-one-foundation --strict` and confirm the scaffold still preserves the approved prototype experience
