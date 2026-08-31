## Verification summary

Date: 2026-08-31

### Production baseline before change

- Last-hour successful chat samples: 4.
- Provider raw first-token P50/P95: 884ms / 962ms.
- Full quick-plus-detail completion P50/P95: 20.7s / 44.2s.
- Server work observed between task-start log and provider timing start: 0.36s to 2.07s.
- Exact click-to-React-first-render was not previously recorded.

### Deterministic structural benchmark

- Repeated validated session reads before the first `task-started` event: reduced from 3 to 1 (66.7% reduction).
- Bound-document refreshes caused by those repeated session reads: reduced to the single authoritative startup refresh.
- Full-session activity writes during admission/question persistence: reduced from 2 to 1 while retaining the authoritative pre-answer touch.
- HTTP clients created for a normal quick-plus-detail answer: reduced from one per provider stage to one reusable bounded gateway client.
- First visible answer event now carries five content-free server timestamps and the browser acknowledges the first rendered answer once.

### Automated verification

- Backend full suite: 391 passed, 14 skipped.
- JavaScript/TypeScript suites: Admin 34, API 90, Desktop 174, Web 329, Protocol 31 passed.
- Workspace typecheck passed for Admin, API, Desktop, Web, Config, and Protocol.
- Production Web build passed with explicit production environment values.
- Existing prompt, normalization, English routing, material grounding, programming, billing, cancellation, and history tests passed; no prompt file changed.
- `openspec validate reduce-live-quick-answer-first-visible-latency --strict` passed.

### Rollback

- Roll back Backend and Web to commit `65907e4f4834fefb958ba6643c329d89aebeab40`.
- No database migration or data rollback is required.
- The additive SSE `timing` field is ignored by older clients.

### Production release

- Runtime commit: `3d0613c02fc327a2ba2818e549c0f410c0749b00`.
- Active live sessions were checked twice and remained zero before the Backend/Web replacement.
- Only Backend and Web were rebuilt and replaced; PostgreSQL, Redis, Admin, Analytics, and desktop release artifacts were not changed.
- Public Backend health and Web build metadata endpoints passed after replacement.
- The production `qwen_chat` integration probe passed against `deepseek-v4-flash` without entering user billing or interview data paths.
- New Backend logs contained no `ERROR`, `CRITICAL`, `Traceback`, or `Exception` entries during release verification.
- Previous Backend/Web images are retained as `rollback-65907e4`; previous hashed Web assets were also retained in the running Web container for already-open browser tabs.
- Exact click-to-first-render improvement will be compared from the first real post-release quick-answer samples now that all stages are measurable.
