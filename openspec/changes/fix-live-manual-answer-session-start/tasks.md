## 1. Contract review

- [x] 1.1 Review current preparation-page `startInterview` flow and confirm it only updates frontend state.
- [x] 1.2 Review backend Session Start API contract and response shape.
- [x] 1.3 Review current manual-answer error extraction and global alert copy.

## 2. Backend session start integration

- [x] 2.1 Add a typed frontend adapter method for starting an Interview Session.
- [x] 2.2 Implement the backend adapter call to `POST /api/v1/sessions/{sessionId}/start`.
- [x] 2.3 Map the backend session response to the existing frontend interview summary/status shape.
- [x] 2.4 Update preparation page start flow to await backend start before navigating.
- [x] 2.5 Add pending and failure state to the preparation page without changing the layout.

## 3. Manual answer error handling

- [x] 3.1 Improve API error normalization so backend envelope error messages are available to UI code.
- [x] 3.2 Update manual answer failure UI to show the actual error message.
- [x] 3.3 Remove the inaccurate default message that tells users to check points or membership for non-billing failures.
- [x] 3.4 Keep billing guidance only for explicit billing/points errors.

## 4. Verification

- [x] 4.1 Add or update frontend tests for successful session start before entering live workspace.
- [x] 4.2 Add or update frontend tests for start failure staying on preparation page.
- [x] 4.3 Add or update frontend tests for manual answer rejected by non-live session showing the real reason.
- [x] 4.4 Run `npm run test -w @offersteady/web`.
- [x] 4.5 Run `./node_modules/.bin/tsc -p apps/web/tsconfig.json --noEmit`.
- [x] 4.6 Run `openspec validate fix-live-manual-answer-session-start --strict`.
