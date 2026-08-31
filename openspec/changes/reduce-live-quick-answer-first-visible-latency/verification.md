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

### Answer render telemetry correction

- Runtime commit: `5f5ddcdf38f04b1cec05282398419e7613253fc9`.
- The browser now returns the five content-free server/SSE timestamps from the first visible chunk together with browser receive/render timestamps; a 100ms render coalescing window cannot discard the first timing envelope.
- `answer-first-render` acknowledgements are retained in the bounded in-memory trace store and expose seven answer-stage distributions without persisting question or answer content.
- Backend full suite: 391 passed, 14 skipped. JavaScript/TypeScript suites: 658 passed. Workspace typecheck, production builds, Python compilation, diff checks, and strict OpenSpec validation passed.
- One unrelated 140ms ASR concurrency timing assertion exceeded its limit while backend and Node suites competed for CPU; it passed three isolated repetitions and the complete backend suite passed when rerun without parallel build load.
- A stale database session remained marked `live`, but it had no activity for about 66 minutes; deployment proceeded only after operational metrics confirmed zero active desktop transports, zero ASR workers, and zero queued audio frames immediately before build and replacement.
- Backend and Web are healthy, the public metrics endpoint exposes the new answer distributions, previous static assets remain available to already-open tabs, and rollback images are retained as `rollback-3d0613c`.
