# Explicit non-thinking web answers — local verification, 2026-09-23

## Scope

Task group 8 adds `reasoning: {"effort": "none"}` only to the DashScope web-search Responses request. The web-search tool, configured model, token budget, timeout, ordinary answer gateway, billing, frontend, and desktop companion are unchanged. Existing unrelated workspace changes are retained.

This change is not deployed. No production configuration, process, or container was changed during this implementation turn.

The local-only statement above describes the original implementation turn. A subsequent user-authorized CN deployment is recorded in [the release record](../../../docs/releases/cn-web-non-thinking-20260923.1.md).

## Verification

- Before the implementation, all three new parameterized tests failed because the outgoing request lacked `reasoning`.
- After the implementation, the focused backend suite passed: **52 tests**.
- Foundation live-answer tests passed: **12 tests**, 85 deselected.
- OpenSpec strict validation and `git diff --check` passed.
- The four synthetic AI evaluation cases parse as JSONL and have unique IDs. The new case documents the non-thinking requirement; this turn did not run a paid model quality evaluation or repeat the earlier live-provider timing comparison.
- The only test warning was the existing Starlette/httpx deprecation warning.

```sh
PYTHONPATH=apps/backend .venv/bin/python -m pytest -q apps/backend/tests/test_web_search_chat_integration.py apps/backend/tests/test_live_answer_stream_executor.py apps/backend/tests/test_interview_usage_billing.py apps/backend/tests/test_redis_live_task_repositories.py apps/backend/tests/test_chat_answer_completeness.py apps/backend/tests/test_web_search_gateway.py
PYTHONPATH=apps/backend .venv/bin/python -m pytest -q apps/backend/tests/test_foundation.py -k live_answer
openspec validate add-web-grounded-detailed-answer --strict
git diff --check
```

## Acceptance checks

- Explicit non-thinking web request: mock transport verifies the actual serialized `reasoning.effort=none`, absence of conflicting `enable_thinking`, and unchanged web tool, model, and output budget.
- Success, provider rejection, and timeout: tests retain success/fallback semantics and assert one request, without a thinking-mode retry.
- Quick-first, detailed-only search, source propagation, cancellation, reservation release, and ordinary answers: existing integration and billing regressions remain green.

This removes reliance on the provider's default thinking mode. It does not guarantee all web requests finish before the existing timeout, introduce streaming, or prove production latency after deployment.
