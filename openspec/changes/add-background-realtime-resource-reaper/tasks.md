## 1. Configuration and lifecycle

- [x] 1.1 Add bounded settings for enabling the reaper and its interval.
- [x] 1.2 Start, cancel, and await one reaper task in FastAPI lifespan without blocking the event loop.
- [x] 1.3 Add realtime service shutdown that closes provider sessions and executors idempotently.

## 2. Reclamation and observability

- [x] 2.1 Add a reaper method that invokes idle-session reconciliation and records non-sensitive counters.
- [x] 2.2 Expose reaper counters in operational metrics.
- [x] 2.3 Ensure persistent ASR sessions are closed when the lifecycle termination path runs.

## 3. Verification

- [x] 3.1 Add regression tests for background reclamation, active-session protection, repeated termination, and shutdown.
- [x] 3.2 Run targeted backend tests and `openspec validate add-background-realtime-resource-reaper --strict`.
