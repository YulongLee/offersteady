## 1. Integration scope and environment baseline

- [x] 1.1 Confirm the end-to-end scenario inventory, real dependency matrix, and prototype-preservation constraints in the change artifacts
- [x] 1.2 Define integration environment prerequisites, synthetic fixture sources, and frontend API-mode requirements
- [x] 1.3 Define the Integration Report schema for provider readiness, scenario readiness, and failure attribution

## 2. Frontend and backend integration wiring

- [x] 2.1 Add a frontend integration runtime path that uses real backend APIs without altering approved prototype interactions
- [x] 2.2 Add backend end-to-end orchestration entrypoints or tests that execute registration, upload, processing, retrieval, session, answer, screenshot, speech, and history flows
- [x] 2.3 Ensure real DashScope, OSS, PostgreSQL, and pgvector dependencies are used throughout end-to-end execution

## 3. End-to-end scenario coverage

- [x] 3.1 Implement Resume / JD / Knowledge upload-to-processing integration scenarios
- [x] 3.2 Implement retrieval-backed Interview Session and Chat Service integration scenarios
- [x] 3.3 Implement Screenshot Answer and Realtime Speech integration scenarios
- [x] 3.4 Implement Conversation Storage and Interview History verification scenarios

## 4. Reporting, logs, and developer guidance

- [x] 4.1 Generate machine-readable and human-readable end-to-end Integration Reports
- [x] 4.2 Add structured logs and request tracing for cross-module failure attribution
- [x] 4.3 Document real-environment setup, execution commands, expected outputs, and troubleshooting guidance

## 5. Validation

- [x] 5.1 Verify the change with `openspec validate establish-end-to-end-integration --strict`
- [x] 5.2 Review the spec scenarios to ensure all requested product flows are represented without introducing new prototype interactions
