## 1. Session state and API

- [x] 1.1 Add backward-compatible database fields and repository mappings for the default-off automatic-answer state and activation time.
- [x] 1.2 Add an owned live-session API to enable or disable automatic answer and return the authoritative state.
- [x] 1.3 Add backend tests for default state, persistence, ownership, live-state validation and activation-boundary resets.

## 2. Automatic trigger safety

- [x] 2.1 Extend live-answer requests with a backward-compatible trigger mode and candidate id.
- [x] 2.2 Validate and claim eligible confirmed interviewer candidates before auto generation, bind the created task, and prevent duplicate billing/tasks.
- [x] 2.3 Add regression tests for old/partial/microphone/low-confidence candidates, duplicate requests, disabled sessions and concurrent generation guards.

## 3. Live page experience

- [x] 3.1 Add the compact default-off automatic-answer switch to desktop and mobile live headers without changing the answer workspace layout.
- [x] 3.2 Persist switch changes and orchestrate eligible confirmed candidates through the existing streaming quick-answer path.
- [x] 3.3 Stop auto triggers on disabled/degraded/replaced/ended states while preserving manual quick answer, screenshots and visible content.
- [x] 3.4 Add Web tests for default-off behavior, future-only triggering, one-task-at-a-time behavior, toggle rollback and manual-path compatibility.

## 4. Evaluation and release verification

- [x] 4.1 Add synthetic AI evaluation cases proving auto and manual triggers share language, programming and grounded-answer behavior.
- [x] 4.2 Update durable product/privacy documentation for the explicit opt-in behavior and data boundary.
- [x] 4.3 Run strict OpenSpec validation, backend tests, Web tests/typecheck/build and production-compatible smoke tests.
- [ ] 4.4 Deploy Backend and Web without restarting PostgreSQL, Redis or the companion, then verify health and default-off production behavior.
