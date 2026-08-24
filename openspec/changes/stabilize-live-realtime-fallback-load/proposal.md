## Why

Production evidence from 2026-08-24 showed that one active interview could raise backend traffic from roughly 10 requests/minute to more than 300 requests/minute. While the realtime SSE subscription was connecting or recovering, the web client continued a one-second fallback loop, and each fallback issued four parallel snapshot requests. High-frequency synchronous Redis/database reads inside async routes then delayed unrelated heartbeats and control APIs on the single backend event loop.

## What Changes

- Treat an accepted realtime SSE transport as healthy before the first application event arrives, while retaining the authoritative initial snapshot.
- Replace the fixed one-second recovery snapshot loop with one non-overlapping bounded backoff loop that pauses while an SSE connect/reconnect is in flight and stops immediately after transport recovery.
- Offload high-frequency synchronous realtime service reads and control writes from FastAPI's async event loop.
- Add regression and synthetic load tests proving that one recovering session cannot create four requests per second or block unrelated async work.

## Capabilities

### New Capabilities

- `bounded-live-realtime-recovery`: Transport health, bounded recovery reconciliation, non-overlap, and event-loop isolation for live sessions.

### Modified Capabilities

None.

## Impact

- Web live-session connection orchestration and recovery policy.
- Backend realtime speech HTTP routes only; transcript, answer, screenshot, billing, and session semantics remain unchanged.
- No database migration, model change, desktop package change, user-facing layout change, or production deployment is included.
