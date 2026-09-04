## Context

The production Companion uses a renderer-owned binding poller and a main-process screenshot SSE loop. Multiple application processes can share the same persisted device identity, and terminal 404/409 screenshot admission responses are currently handled as transient failures. This amplifies control traffic while the backend also owns process-local realtime state.

## Goals / Non-Goals

**Goals:**

- Guarantee one Companion process owns a product profile at a time.
- Keep binding reads and screenshot stream ownership single-flight.
- Suspend terminal invalid screenshot bindings and wake promptly for a new binding.
- Preserve current capture, answer, layout, endpoint and privacy contracts.

**Non-Goals:**

- Changing ASR models, audio framing, transcripts, answers or billing.
- Adding Uvicorn workers before process-local realtime owners become worker-safe.
- Persisting user content for diagnostics.

## Decisions

### Claim the profile lock before readiness

The main process claims `app.requestSingleInstanceLock()` after selecting its stable profile and before runtime loops start. A second launch restores and focuses the primary window, then exits.

### Suspend terminal screenshot admission

Explicit 404/409 admission responses suspend the invalid stream without fallback polling. Network failures and retryable server responses retain bounded recovery. A meaningful binding eligibility transition wakes one new stream owner.

### Preserve short duplicate-read protection

Successful content-free active-connection reads remain briefly cached below the live poll interval, keyed by device and pinned binding identity, with mutation invalidation. Generic 429 rate limiting is not introduced.

### Do not add backend workers

Realtime lifecycle ownership remains process-local, so worker scaling is outside this rollout.

## Migration Plan

1. Capture the domestic rollback baseline and confirm zero active interviews.
2. Build signed artifacts from a clean domestic release worktree.
3. Publish immutable artifacts before switching the backend manifest.
4. Recreate only the domestic backend and run public health/download smoke tests.
5. Roll back the backend image and manifest if acceptance fails; retain all data volumes.

## Open Questions

None.
