# Independent quick-answer completion — local verification

Date: 2026-09-23. Scope: task group 10 only; no production deployment or configuration changes.

## Behavior changed

- The streaming service persists `quick_answer_completed` and emits a non-terminal `quick-completed` event after the quick answer and any completeness continuation finish, before waiting for detailed retrieval or web search.
- The event is exposed through SSE, task snapshots and realtime task notifications. The task remains active; billing is not settled at the quick-stage boundary.
- The browser flushes the first text chunk and stage completion immediately. The quick section stops streaming and formats its Markdown independently; the detailed section retains its own pending state.
- Detailed failure or stream interruption retains completed quick text. Same-task progress cannot regress, and cancelled/obsolete request callbacks cannot overwrite the current answer.
- Whole-task cancellation, duplicate-submit protection, ordinary answer requests, search/model configuration, timeout and charging rules are unchanged. No desktop companion upgrade is involved.

This fixes presentation/stage coupling. It does not claim to reduce provider first-token latency, web retrieval time or proxy/network buffering.

## Executed checks

The new regressions failed before the runtime changes: four backend cases demonstrated a missing quick completion boundary, and five answer-card cases demonstrated shared streaming state and missing failure preservation. They passed after the changes.

```sh
PYTHONPATH=apps/backend .venv/bin/python -m pytest -q apps/backend/tests/test_web_search_chat_integration.py apps/backend/tests/test_live_answer_stream_executor.py apps/backend/tests/test_interview_usage_billing.py apps/backend/tests/test_redis_live_task_repositories.py apps/backend/tests/test_chat_answer_completeness.py apps/backend/tests/test_web_search_gateway.py --tb=short
PYTHONPATH=apps/backend .venv/bin/python -m pytest -q apps/backend/tests/test_foundation.py -k live_answer --tb=short
npm run test -w @offersteady/web -- src/App.focused-live.test.tsx src/AnswerActionBar.test.tsx src/AnswerWorkspace.test.tsx src/backend-adapter.test.ts src/live-answer-stream.test.ts src/live-workspace.test.ts
npm run typecheck -w @offersteady/web
VITE_APP_ENV=production VITE_API_BASE_URL=/ VITE_PUBLIC_APP_VERSION=0.1.0 npm run build -w @offersteady/web
openspec validate add-web-grounded-detailed-answer --strict
git diff --check
```

- Backend: 57 focused tests plus 12 live-answer foundation tests passed (69 total). Foundation SSE checks confirm the completion event is still non-terminal and precedes detailed content.
- Frontend: 123 tests across six files passed. Includes desktop/mobile delayed detail, fallback, cancellation, late callbacks, disconnected detail, legacy responses and monotonic same-task progress.
- Type check, production build, strict specification validation and whitespace check passed.
- Browser visual check: real React answer component with synthetic text, at 1440px and 390px, for pending detail and failed detail (four cases). Quick Markdown remained visible and complete, pending detail stayed separately busy, failure retained the quick text, and no horizontal overflow was detected. Screenshots were inspected locally.
- Local screenshot and probe artifacts: `/tmp/offersteady-quick-stage-review-HQEJU6/`. The browser harness uses a fresh profile, blocks API requests and uses no real interview data.

These are focused local tests, not a full-repository green result or a live paid-provider/browser end-to-end latency measurement. Existing unrelated workspace changes were retained.

## Release handoff

- This change has not been deployed to CN or Global. Reconcile only the relevant files against the current production baseline and obtain deployment instruction before release.
- New code accepts historical task records without the completion field. New UI also accepts older responses and falls back to the detailed-answer delimiter.
- The Redis task serializer stores the new dataclass field. A backend rollback to an older decoder that rejects unknown fields is not automatically safe for newly written task records: retain the additive field/decoder compatibility when preparing the rollback image, or separately plan compatible runtime-record handling. Do not clear active tasks to work around this.
- Do not infer safe release scope from the whole dirty worktree or use the local build wholesale without reconciling unrelated changes.
