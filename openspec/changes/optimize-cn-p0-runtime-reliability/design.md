## Context

The current capacity sampler falls back to `/proc/meminfo` when Docker exposes no cgroup limit, so the dashboard's container label is inaccurate. Interview cleanup exists but needs explicit end-state verification for all session resources. Live measurements show one successful quick answer with server first-visible latency around 1.6 seconds but browser click-to-render around 3.6 seconds, leaving a meaningful unexplained interval.

## Goals / Non-Goals

**Goals:**

- Use container RSS/cgroup usage and expose host usage separately.
- Make end/cancel/idle cleanup idempotent and observable.
- Preserve quick-answer streaming while reducing pre-first-display waiting and retaining stage diagnostics.

**Non-Goals:**

- No UI redesign, model/provider replacement, prompt changes, or raw audio/transcript persistence.
- No new infrastructure dependency or cross-region deployment.

## Decisions

- **Resource metrics:** keep the existing capacity API but add explicit host fields and derive container memory from `/proc/self/status` RSS when cgroup `memory.max` is unlimited. This is more truthful than using host available memory as a container metric; adding a separate field preserves API compatibility.
- **Cleanup:** reuse the existing service lifecycle and reaper, adding idempotent finalization hooks and bounded joins/cancellation. A new worker system would add complexity without improving the prototype's core path.
- **Latency:** retain the current streaming executor and instrument each boundary; move only demonstrably pre-first-token work out of the critical path. Full answer generation remains asynchronous after the quick stage.
- **Validation:** synthetic unit/integration tests plus a read-only production smoke check. Production deployment uses an image tag and retains the prior image for rollback.

## Risks / Trade-offs

- [Risk] RSS differs from cgroup charge for shared pages → report both when available and label the source.
- [Risk] Cancellation races with provider callbacks → make cleanup idempotent and tolerate already-closed resources.
- [Risk] More telemetry fields increase event size → omit null fields and never include content.

## Migration Plan

1. Run focused tests and build a tagged backend image.
2. Deploy only the backend container with the previous image retained.
3. Verify health, capacity fields, quick-answer smoke path, and cleanup metrics.
4. Roll back the backend image if health or smoke checks fail.

## Open Questions

- The acceptable product target for click-to-first-visible quick-answer latency should be confirmed after collecting more than one live sample.
