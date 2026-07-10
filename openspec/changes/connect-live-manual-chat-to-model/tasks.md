## 1. Scope and contract review

- [x] 1.1 Review current live interview manual question flow in `apps/web/src/App.tsx`.
- [x] 1.2 Review `InterviewAppAdapter` and backend adapter contracts for adding a manual answer submission method.
- [x] 1.3 Review existing backend Live Answer API schemas and tests for `/api/v1/live-answer/questions`, task lookup, cancellation, and history.

## 2. Frontend adapter integration

- [x] 2.1 Add a typed adapter method for submitting a manual live question.
- [x] 2.2 Implement the backend adapter call to `POST /api/v1/live-answer/questions` using current auth and session identity.
- [x] 2.3 Map backend live-answer task responses into existing answer workspace state without changing the UI layout.
- [x] 2.4 Ensure manual answer history reloads through backend state/history rather than local-only generated state.

## 3. Live page behavior

- [x] 3.1 Replace local synthetic manual answer creation in `submitManual` with the adapter call.
- [x] 3.2 Show a pending/generating state while the backend model request is in flight.
- [x] 3.3 Render backend success, failure, and non-terminal task states in the existing answer area.
- [x] 3.4 Keep “回答问题” in the compact question bar and do not add local desktop software readiness checks.
- [x] 3.5 Keep cancellation wired to backend answer task identifiers.

## 4. Billing, usage, and error handling

- [x] 4.1 Remove or neutralize any frontend-only authoritative point deduction for manual answers.
- [x] 4.2 Ensure backend-returned usage or refreshed aggregate state is used for displayed usage facts.
- [x] 4.3 Add clear user-facing errors for backend/model failures without creating fake successful answers.
- [x] 4.4 Prevent duplicate manual submissions for the same in-flight command.

## 5. Verification

- [x] 5.1 Add or update frontend tests for manual question success, failure, pending state, duplicate-submit prevention, and cancellation.
- [x] 5.2 Add or update backend contract tests only if the existing Live Answer API contract changes. Backend API contract did not change.
- [x] 5.3 Run `npm run test -w @offersteady/web`.
- [x] 5.4 Run `./node_modules/.bin/tsc -p apps/web/tsconfig.json --noEmit`.
- [x] 5.5 Run relevant backend tests for live-answer if backend code changes. Backend code was unchanged.
- [x] 5.6 Run `openspec validate connect-live-manual-chat-to-model --strict`.
