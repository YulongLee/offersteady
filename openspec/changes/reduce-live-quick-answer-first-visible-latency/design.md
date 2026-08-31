## Context

The live-answer SSE route currently validates and refreshes the same interview session several times while appending the explicit question and building the conversation window. Each session refresh also reloads every bound document. The Qwen-compatible adapter additionally creates a new synchronous HTTP client for every quick, detail, and continuation request. Production samples show provider raw first-token latency near one second, but server preparation adds a variable sub-second to multi-second delay before the provider request begins.

The optimization must preserve the existing prompt order, normalized-question envelope, selected-material grounding, English enforcement, programming policy, billing reservation, cancellation, Redis recovery, and dedicated answer SSE contract. It must not expose question, answer, resume, JD, or transcript content through telemetry.

## Goals / Non-Goals

**Goals:**

- Reuse one authoritative session/material snapshot throughout one answer startup.
- Preserve durable question history while removing redundant session refresh and activity writes.
- Reuse provider TCP/TLS connections through a bounded shared HTTP client.
- Measure provider-start, first raw token, first visible SSE event, browser receive, and browser render stages with content-free metadata.
- Keep every optimization independently reversible and prove existing answer behavior with regression tests.

**Non-Goals:**

- No model, endpoint, prompt, normalization protocol, answer length, or retrieval-policy change.
- No billing rule, point rate, membership, idempotency, or settlement change.
- No Redis answer checkpoint redesign, delta-only SSE migration, UI layout change, or artificial typing animation.
- No Uvicorn worker-count change in this rollout.

## Decisions

### Reuse a validated session snapshot inside the answer operation

Session service methods used by Chat Service accept an already validated session record for internal use. Appending the question still writes the same context entry, but it does not refresh the same session and every bound document again. Reading the recent context window also reuses this snapshot. The explicit activity touch performed immediately before the append remains authoritative, so the append path can skip a duplicate full-session save.

Alternative: introduce a request-local ORM/session cache across every repository. Rejected because it is a much larger architectural change than the measured hot path requires.

### Keep billing reservation synchronous and unchanged

The answer is still admitted only after the existing idempotent billing reservation succeeds. Billing cleanup, entitlement checks, locking, and settlement semantics are not changed in this rollout, even though they remain candidates for later profiling.

Alternative: reserve after the first token. Rejected because it could generate unpaid answers and changes commercial behavior.

### Own one bounded HTTP client per Qwen-compatible gateway

The gateway lazily owns one thread-safe `httpx.Client` configured with the existing timeout and bounded connection limits. Quick, detail, continuation, and non-stream requests share it. Dependency lifecycle code closes it during application shutdown; tests can inject or replace the transport without real network calls.

Alternative: create an async provider gateway immediately. Rejected because the current SSE iterator deliberately runs synchronously in Starlette's thread pool and an async migration would broaden the change.

### Add stage telemetry without changing the answer envelope

The task records opaque timestamps for server acceptance, provider request start, first raw provider token, first visible answer event, and SSE yield. The browser acknowledges the first non-empty answer render once. Telemetry stores only trace/task identifiers, timestamps, durations, language, status, and size buckets; it never stores content.

The `answer-first-render` acknowledgement persists the server timestamps echoed by the first SSE chunk together with browser receive/render timestamps. The performance summary derives same-clock server and browser stage durations separately; cross-device wall-clock subtraction is not used as an authoritative latency measurement.

Alternative: infer first-visible latency from provider `first_token_ms`. Rejected because normalization output is intentionally hidden and the provider metric cannot represent the user-visible result.

## Risks / Trade-offs

- [A stale material snapshot is reused during one answer] → The snapshot exists only for the duration of the explicit answer operation; a later answer performs a fresh authoritative read.
- [Skipping the append-time session save could lose activity] → The route retains the immediately preceding authoritative activity update and regression tests verify `last_activity_at_ms` advances.
- [A shared HTTP client can exhaust its pool] → Configure bounded limits above expected concurrent answer calls, preserve request timeouts, and expose safe provider failure codes.
- [Shared-client tests could leak resources] → Provide an explicit close method and close injected clients in fixtures/application shutdown.
- [Telemetry adds work to the hot path] → Record timestamps in memory and submit browser acknowledgement best-effort; telemetry failure must never fail an answer.

## Migration Plan

1. Add regression tests and stage timing fields behind production-safe configuration.
2. Deploy the session-snapshot optimization and shared provider client together to a local synthetic environment.
3. Run backend, web, AI eval, typecheck, build, billing, normalization, English, cancellation, and history tests.
4. Build a rollback image, deploy only Backend and Web, then verify health, errors, first-token metrics, billing, and a synthetic live-answer stream.
5. Roll back Backend/Web images independently if error rate, answer correctness, or billing consistency regresses.

## Open Questions

None. Answer-first protocol and Redis delta checkpointing remain separate future changes after this behavior-preserving rollout is measured.
