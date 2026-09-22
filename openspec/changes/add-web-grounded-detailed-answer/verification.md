# Web-mode switching regression verification — 2026-09-23

## Scope and outcome

This record covers task group 6 only. The earlier release checkboxes do not mean this regression fix has been deployed.

- Each intentional answer attempt now has a unique, mode-aware billing request ID. In-flight duplicate clicks remain suppressed.
- Switching web mode off detaches and cancels only an in-flight web answer, unlocks ordinary quick answer, and retains generated simple-answer text with an incomplete-answer warning.
- Late stream responses, cleanup callbacks, realtime events, and workspace refreshes cannot replace the new answer with the cancelled web task.
- A cancelled task cannot be revived by a delayed search result. Stream disconnect cleanup also covers cancellation before the browser receives the task ID; reservations are released through the backend cancellation path.
- Failed/cancelled manual-answer retries create a real new request. Unexpected stream termination returns a recoverable failure instead of leaving the button stuck processing.
- Models, prices, provider timeout, desktop companion, and production configuration were not changed by this fix.

An already-running synchronous provider call may continue until it returns or reaches its existing timeout. The browser is unlocked immediately; the cancelled task remains cancelled, and late results must not be settled as a successful web answer.

## Local verification

All test samples are synthetic. Provider calls and billing stores used by these regression tests are mocked or in-memory; no real user records or paid provider calls were used.

| Check | Result |
| --- | --- |
| Frontend focused regression suite (six files below) | 113 passed |
| Backend focused regression suite (six files below) | 49 passed |
| Foundation live-answer tests | 12 passed, 85 deselected |
| Web TypeScript check | Passed |
| Production web build | Passed |
| OpenSpec strict validation | Passed |
| Git whitespace/error check | Passed |

Commands executed from the repository root:

```sh
npm run test -w @offersteady/web -- src/App.focused-live.test.tsx src/AnswerActionBar.test.tsx src/AnswerWorkspace.test.tsx src/backend-adapter.test.ts src/live-answer-stream.test.ts src/live-workspace.test.ts
npm run typecheck -w @offersteady/web
VITE_APP_ENV=production VITE_API_BASE_URL=/ VITE_PUBLIC_APP_VERSION=0.1.0 npm run build -w @offersteady/web
PYTHONPATH=apps/backend .venv/bin/python -m pytest -q apps/backend/tests/test_web_search_chat_integration.py apps/backend/tests/test_live_answer_stream_executor.py apps/backend/tests/test_interview_usage_billing.py apps/backend/tests/test_redis_live_task_repositories.py apps/backend/tests/test_chat_answer_completeness.py apps/backend/tests/test_web_search_gateway.py
PYTHONPATH=apps/backend .venv/bin/python -m pytest -q apps/backend/tests/test_foundation.py -k 'live_answer'
openspec validate add-web-grounded-detailed-answer --strict
git diff --check
```

Covered transitions include completed/failed web answer → same-question ordinary answer; repeated ordinary attempts; cancellation before task acknowledgement on desktop and mobile; retained text; late completion/realtime updates; cancellation during search and before detailed delivery; reservation release; normal-answer toggle isolation; failed retry; and truncated SSE recovery.

## Broader checks are not fully green

The full frontend run reported 424 passed and 9 failed before the final two regression cases were added. One failure was a missing refresh token in the new synthetic fixture; this was corrected and verified in the final focused run above. The other eight failures concern files not changed by this fix:

- Three Nginx release-contract assertions: public www normalization, legal noindex, and partner-program routing.
- Four CSP-hash assertions for realtime-interview, AI-interview-assistant, pricing, and download public pages.
- One product-experience homepage-title assertion.

The full frontend suite was not rerun after correcting the fixture, so no final full-suite pass count is claimed.

A broader backend filter (`-k 'chat or live_answer'`) also selected a WeChat test: 14 passed and 1 failed. That test expects `wechat-production-disabled`, while the response reports `domain_request_error`. Authentication behavior was not modified here; the precise live-answer subset subsequently passed as recorded above.

## Release boundary

This turn performed local development and testing only. It did not deploy, restart production, change accounts, or upgrade a desktop companion.

Subsequent user-authorized deployment is recorded separately in [the CN release record](../../../docs/releases/cn-web-mode-switching-fix-20260923.1.md). The local-development boundary above describes the original development turn, not the subsequent release.

Before a later authorized CN deployment, reconcile these scoped changes against the then-current CN release, preserve regional configuration/features and unrelated work, confirm there are no live interviews, and prepare a rollback. Do not replace production configuration or the whole regional release with the local workspace wholesale. Live end-to-end acceptance remains to be performed after that authorized release.
