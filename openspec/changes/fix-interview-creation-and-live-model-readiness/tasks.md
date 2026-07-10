## 1. Interview creation and roster maintenance

- [x] 1.1 Review the current interview creation path in frontend adapters and backend session APIs to identify why new interviews fail.
- [x] 1.2 Fix new interview creation so the UI only inserts a session after backend creation succeeds and shows a real error on failure.
- [x] 1.3 Enforce a five-item recent interview roster in the backend-facing dashboard/app state contract.
- [x] 1.4 Add delete actions and refresh behavior for recent interviews so users can maintain the roster safely.

## 2. Manual-mode interview start without extra token gates

- [x] 2.1 Audit the start-interview flow for user-visible token, publisher credential, or equivalent blockers in Web manual mode.
- [x] 2.2 Update the prepare-to-live transition so manual-mode start only depends on successful session start, not extra token prerequisites.
- [x] 2.3 Ensure backend session start initializes the state needed for later manual answers without exposing extra token setup to the user.

## 3. Real model runtime for manual answers

- [x] 3.1 Audit the live manual answer path and remove any remaining mock, fixture, or local synthetic fallback from the runtime path.
- [x] 3.2 Connect fast answer/manual question submission to the real backend Chat Service using the current `.env` model configuration.
- [x] 3.3 Normalize frontend error presentation so session-start, session-missing, and model-runtime failures show the real safe backend reason.

## 4. Verification

- [x] 4.1 Add regression tests for new interview creation success/failure and recent-roster truncation/delete behavior.
- [x] 4.2 Add regression tests for start-interview in Web manual mode without extra token gating.
- [x] 4.3 Add integration coverage proving manual fast-answer hits the real backend runtime contract instead of mock output.
- [x] 4.4 Run `openspec validate fix-interview-creation-and-live-model-readiness --strict`.
