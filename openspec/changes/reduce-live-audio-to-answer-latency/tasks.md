## 1. Automatic Answer Streaming

- [x] 1.1 Add a Chat Service automatic-answer generator that preserves the existing automatic prompt, retrieval, persistence, usage, billing, failure, and cancellation behavior while yielding ordered provider chunks.
- [x] 1.2 Move confirmed-question answer generation to a bounded background executor so the realtime audio worker returns before model completion.
- [x] 1.3 Publish compact automatic-answer start/progress/terminal snapshots through the realtime event stream with candidate/task idempotency.
- [x] 1.4 Add backend regression tests for first-chunk-before-completion, continued audio ingest, failure/cancellation, history, and single billing settlement.

## 2. Web Reconciliation and Transcript Rendering

- [x] 2.1 Map automatic-answer stream snapshots into the existing live answer workspace without changing its layout or controls.
- [x] 2.2 Replace the fixed two-character transcript animation with bounded adaptive catch-up and immediate final rendering.
- [x] 2.3 Remove redundant realtime render scheduling where safe and add focused frontend tests for reconnect/replay, terminal precedence, and 100-character catch-up.

## 3. Desktop Endpointing

- [x] 3.1 Tune system-audio silence finalization to 500 ms and microphone finalization to 700 ms while retaining segment assembly and suppression behavior.
- [x] 3.2 Add desktop regression tests for the new endpoint windows, partial cadence, natural-pause segmentation, and one-final-per-segment behavior.

## 4. Evaluation and Release

- [x] 4.1 Add or update AI eval coverage for streamed automatic-answer completeness and safe partial failure.
- [x] 4.2 Run focused backend, web, desktop, typecheck, build, and synthetic latency tests; record before/after timings.
- [x] 4.3 Run `openspec validate reduce-live-audio-to-answer-latency --strict` and review the production diff for unrelated changes.
- [x] 4.4 Commit only the scoped performance change, push it to Git, deploy with the guarded release workflow, and verify production health plus the live audio-to-answer path.
