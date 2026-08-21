## Why

The live interview path is functionally complete, but screenshot answers still remain blank until the vision provider finishes, realtime delivery performs frequent empty Redis reads, and active answer/screenshot tasks are lost when a backend process restarts. These issues limit perceived speed, production observability, and safe horizontal scaling even though the current low-load happy path works.

## What Changes

- Stream screenshot answer text to the existing answer workspace as soon as the vision provider emits usable text while preserving the current screenshot-only prompt, billing, cancellation, and final answer semantics.
- Persist live-answer tasks, screenshot tasks, capture requests, upload metadata, and idempotency-relevant state in Redis with bounded TTL in production, while retaining in-memory adapters for tests.
- Replace fixed 100 ms Redis event polling with blocking cursor reads that wake on new session events and retain snapshot/resume compatibility.
- Decouple realtime ASR audio append from transcript delivery so the ingest worker does not synchronously wait for a partial result after every frame; keep per-source ordering, finalization, recovery, and no-audio-persistence guarantees.
- Prefetch detailed-answer retrieval during the quick-answer stage without delaying first-token delivery or changing the visible quick/detail answer structure.
- Add privacy-safe end-to-end timing identifiers and browser render acknowledgements for transcript, quick-answer, and screenshot-answer paths; do not record audio, screenshots, questions, or answer text in performance telemetry.
- Preserve all current public controls and behavior: speech never auto-generates an answer, only explicit quick/manual/screenshot actions bill points, and older desktop packages retain fallback compatibility.

## Capabilities

### New Capabilities

- `streaming-screenshot-answer-delivery`: Incremental screenshot-answer delivery, monotonic reconciliation, cancellation, and terminal recovery.
- `persistent-live-task-runtime`: Redis-backed transient answer and screenshot task state with TTL, restart recovery, and test adapters.
- `low-latency-session-runtime`: Blocking session-event delivery, asynchronous per-source ASR processing, and detailed-answer retrieval prefetch.
- `privacy-safe-runtime-performance-telemetry`: Correlated client-to-server timing stages and aggregate performance reporting without sensitive payloads.

### Modified Capabilities

None.

## Impact

- Backend: realtime speech gateway/service, Redis realtime repository, chat and screenshot repositories/services/routes, configuration, schemas, and telemetry.
- Web: live session reducer, answer/screenshot streaming adapters, render acknowledgement, and recovery behavior.
- Desktop: only protocol-compatible timing metadata if required; no permission, capture UI, installer, or release-format change is intended.
- Infrastructure: existing Redis is reused; no new external service or PostgreSQL migration is required.
- Deployment remains backward compatible and can be rolled back independently per web/backend service.
