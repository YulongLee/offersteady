# Verification

Verified on 2026-08-28 from the repository root.

## Automated checks

- Focused Backend language, completeness, screenshot, prompt/eval, and logging tests: `39 passed`.
- Full Backend suite: `359 passed, 14 skipped`; two unrelated ASR prewarm wall-clock assertions exceeded their thresholds under the full parallel workload, then both passed when rerun together (`2 passed`).
- Focused Web answer-surface tests: `4 passed`.
- Full Web suite: `310 passed, 1 failed`. The existing material-delete test expects `无法连接后端基础服务`, while the unchanged application currently renders `文档不存在。`; neither the test nor that material flow is modified by this change.
- Web TypeScript check: passed.
- Production Web build with `VITE_APP_ENV=production`, same-origin API, and public version `1.2.11`: passed.
- Python compile check for both modified services: passed.
- `git diff --check`: passed.
- `openspec validate enforce-english-interview-answer-language --strict`: passed.

## Real provider smoke test

The locally configured OpenAI-compatible provider was called with synthetic Chinese question, title, history, resume, and knowledge evidence for an authoritative `en-US` session. The configured model was `deepseek-v4-flash` on the public DashScope host.

- Quick template: `interview-chat-en-quick`; normalized question and answer passed the English guard.
- Detail template: `interview-chat-en-detail`; answer passed the English guard.
- Only configuration presence, provider/model, endpoint host, template IDs, character counts, and boolean guard results were printed. No API key, prompt, evidence, or generated answer was printed or logged.

## Deployment and rollback scope

Only Backend, Web, prompt/eval, and specification files changed. `apps/desktop` and the desktop/WebSocket protocols are unchanged, so no companion-app build or version bump is required.

Deploy Backend and Web together so the server enforcement and English answer-card framing become active atomically. Roll back by restoring the previous Backend and Web images together. There is no database migration, persisted source translation, or session-data migration to reverse.
