## Context

The primary live-session transport is SSE. The current web orchestration marks the stream healthy only after an application snapshot/update callback. A separate one-second interval runs while that flag is false, even when the SSE fetch is already in flight or a reconnect timer is active. Each fallback calls transcripts, candidates, events, and runtime in parallel. Production observed more than 300 requests/minute for one active interview and correlated API P95 above one second.

The corresponding FastAPI routes are declared `async` but call synchronous service/repository code directly. Under request amplification, Redis and PostgreSQL calls block the shared event loop and increase latency for heartbeats, capture control, admin APIs, and other users.

## Goals / Non-Goals

**Goals:**

- Keep SSE as the primary authoritative transport.
- Stop recovery snapshots while an SSE transport is connected or connecting.
- Bound degraded-mode snapshots with non-overlap and exponential backoff.
- Keep synchronous repository work away from the async event loop.
- Preserve current session ownership, cursor recovery, lease replacement, and UI behavior.

**Non-Goals:**

- No model, prompt, ASR segmentation, answer, screenshot, billing, or desktop behavior changes.
- No multi-worker or multi-instance deployment in this change.
- No production deployment during implementation.

## Decisions

### Expose transport-open separately from application updates

The adapter subscription options gain an optional transport-connected callback. It fires only after an authenticated successful response with a readable SSE body. The live page uses it to stop fallback reconciliation immediately; the initial SSE snapshot remains responsible for visible state hydration.

### Use one scheduled recovery loop

Replace the permanent one-second interval with a scheduled timeout. Recovery waits five seconds initially and backs off to fifteen seconds. It does not run while the stream is healthy, a subscription is in flight, or the page is replaced/hidden. Reconnect and snapshot recovery may be scheduled independently, but only one subscription and one snapshot can be in flight.

### Offload synchronous route work

High-frequency async routes invoke synchronous service methods through `asyncio.to_thread`. This preserves route contracts and repository behavior while preventing Redis/database waits and JSON preparation from blocking unrelated coroutines.

## Risks / Trade-offs

- A delayed first SSE snapshot no longer triggers an immediate fallback read. The transport has already been accepted, so waiting for its authoritative snapshot avoids duplicate load; reconnect handling remains available if it closes.
- Thread offload consumes the default bounded worker pool. Removing request amplification keeps demand bounded, and the dedicated blocking-event pool remains separate.
- Recovery snapshots may appear several seconds later during a real stream outage. Explicit answer and screenshot controls remain available; five-second recovery is preferable to self-amplifying one-second polling.

## Rollback

Revert the web recovery scheduler and route offload changes. No schema or persisted data rollback is required.

## Verification evidence

- Production read-only baseline: one active interview reached about 309 requests/minute; the four fallback snapshot endpoints each received about 28 requests/minute, while API P95 reached 1.12 seconds and host CPU monitoring reached 42% on two cores.
- Healthy-stream regression: after the initial snapshot load and accepted SSE transport, a 1.2-second observation window produced no repeated fallback snapshot.
- Degraded-mode calculation: the old fixed cadence could create 240 snapshot subrequests/minute; the 5/10/15-second capped cadence creates at most about 20 subrequests in the first minute, a reduction of about 91.7%, before accounting for successful SSE recovery.
- Event-loop regression: a synchronous service wait released by an event-loop timer completed in under 200 ms, proving the wait ran outside the event loop.
