## Context

The production path is Electron microphone/system capture -> multiplexed WebSocket v2 -> FastAPI source worker -> persistent Qwen realtime ASR -> Redis cursor stream -> browser reducer. Production metadata shows healthy transport and queue latency, but the current process accepted an already-live desktop transport without running provider prewarm, exposed one global capture state while the system channel produced no frames, and lacks a complete browser first-visible trace. Normal finalization is fast, but a missing provider completion holds the source lock for up to eight seconds after the source watchdog has already stopped tracking the final frame. A reconnect retry can then lack the complete utterance.

The change must preserve protocol-v2 compatibility, the current live-page layout, independent microphone/system roles, explicit-only answer generation, and the rule that raw audio is never persisted.

## Goals / Non-Goals

**Goals:**

- Make `live-ready` mean the bound desktop transport, enabled capture sources, provider connections, and browser event consumer are ready for immediate speech.
- Recover readiness when an already-live interview reattaches after a backend or desktop restart.
- Keep audio ingestion bounded while a provider commit is pending and ensure every visible partial reaches `final` or `incomplete` within four seconds.
- Retry a failed provider turn only with a complete, bounded in-memory utterance.
- Meet click-to-ready, first-visible, and stop-to-terminal acceptance gates with content-free telemetry.
- Ship a local macOS companion 1.2.2 without layout or brand changes.

**Non-Goals:**

- No provider/model migration, server-VAD rollout, automatic answer generation, production deployment, or redesign.
- No raw-audio, transcript-text, credential, or personal-material persistence in diagnostics.
- No promise that unavailable operating-system permissions can be repaired without user action.

## Decisions

### Represent readiness per source and derive the global state

Desktop status will report microphone and system capture health independently. Backend runtime will combine transport presence, capture source health, provider state, and event-consumer state into `preparing`, `ready`, or `degraded`; the Web keeps the current layout and projects that truth into its existing status area. An active interview or connected transport alone is insufficient to claim readiness.

A global boolean was rejected because it currently masks the production case where one transport is active but the system source never produces audio.

### Rewarm on both lifecycle start and publisher attachment

The normal start API keeps its bounded concurrent prewarm. Creating or resuming an authenticated publisher for an already-live, capturing interview also schedules an idempotent per-source warm operation. This reconstructs process-local provider sessions after backend restart without relying on an HTTP start request being repeated. A first frame may still use the existing single-flight lazy path during provider failure.

Persisting provider WebSockets in Redis was rejected because sockets are process-local; reconstructing them from shared lifecycle state is simpler and replaceable.

### Keep a bounded source-turn replay buffer in backend memory

Each source worker accumulates ordered PCM for the active segment up to the existing hard-turn duration and a strict byte cap. The buffer is deleted on authoritative final, incomplete recovery, pause, end, retirement, or TTL expiry and is never serialized. On a retry that recreates the provider session, the gateway receives a synthetic recovery frame containing the complete buffered utterance rather than only the terminal tail.

Relying on terminal resend from the desktop was rejected because the existing terminal acknowledgement confirms admission before provider completion and the desktop may safely discard earlier frames. Persisting PCM was rejected for privacy reasons.

### Keep `committing` under the watchdog and separate admission from completion

Terminal admission remains immediately acknowledged and prioritized, but the source-turn record transitions to `committing` instead of being removed. The watchdog covers this state until provider completion. Provider work stays ordered per source, while subsequent frames are admitted into the bounded worker/replay buffer rather than being discarded. Missing completion publishes one monotonic `incomplete` terminal event and recreates only the affected provider source.

Lowering only the silence tail was rejected because production normal stop-to-final is already below one second and it cannot fix a missing provider completion.

### Preserve complete text over blind retry

A retry after connection failure is allowed once only when complete buffered PCM is available. If it is not available or the bounded deadline expires, the system preserves the latest stable partial as `incomplete`, clears the busy state, and starts a clean provider source for the next segment. It never retries a terminal tail as if it were a complete utterance.

### Use content-free end-to-end acceptance telemetry

Trace stages will count readiness, first frame, provider first partial, event append, SSE delivery, browser store, and paint without text or PCM. Per-source missing-frame/readiness counters distinguish silence from capture unavailability. Release acceptance uses synthetic or authorized speech and records only latency distributions and terminal outcomes.

## Risks / Trade-offs

- [An in-memory utterance buffer increases memory under concurrency] -> Cap bytes per source to the configured hard-turn envelope, clear deterministically, expose aggregate buffered bytes, and reject unbounded growth.
- [Rewarm on attachment can open duplicate provider sockets] -> Reuse the gateway's per-session-source single-flight lock and idempotent session map.
- [A four-second terminal deadline can precede a late provider final] -> Mark the source generation retired and enforce terminal precedence so late events cannot reopen it.
- [System audio can be intentionally silent] -> Treat capture-graph readiness separately from speech frames; silence is ready, an unopened/failed graph is degraded.
- [Readiness gating could delay navigation during provider outage] -> Bound the gate, show truthful degraded state, and keep manual/screenshot paths usable.
- [Protocol additions can reach older clients] -> Add optional fields only and retain protocol 2.0 framing.

## Migration Plan

1. Add protocol, backend, desktop, and Web regressions before changing defaults.
2. Implement backend attachment rewarm, committing watchdog coverage, and bounded ephemeral replay with feature flags and metrics.
3. Implement desktop per-source readiness reporting and Web projection without structural layout changes.
4. Increment only desktop patch metadata to 1.2.2, run focused and full local verification, and build the signed/local macOS artifact.
5. Start the local 1.2.2 companion for user acceptance. Production remains unchanged until a later explicit approval.
6. For a later rollout, deploy backward-compatible backend/Web before publishing the desktop manifest; rollback by restoring prior images/manifest or disabling readiness/replay flags.

## Open Questions

None blocking implementation. Production promotion and Windows release packaging remain separate explicit actions after local acceptance.
