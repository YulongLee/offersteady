## Context

Production evidence separates a healthy model first-token time from a much slower browser click-to-first-render time. The current FastAPI route returns a `StreamingResponse` backed by a synchronous iterator; Starlette schedules that iterator on its shared worker pool. The first server timestamp is currently taken inside the iterator, so time between route receipt and iterator execution is invisible and can be amplified by unrelated synchronous control traffic.

Backend source is shared by Chinese and Global editions, but production stacks are independent. Chinese production currently has active users and is excluded from this rollout. Global provides an isolated pilot environment with its own containers, database, Redis, domain and rollback images.

## Goals / Non-Goals

**Goals:**

- Bound and isolate live-answer stream execution from unrelated synchronous request work.
- Make the missing request-receipt-to-generator interval measurable.
- Render the first Global answer chunk without a deliberate coalescing delay.
- Preserve all answer, evidence, billing and privacy behavior.
- Deploy only to Global and retain immediate Backend/Web rollback.

**Non-Goals:**

- No model, provider endpoint, Prompt, RAG, answer length or language-policy changes.
- No Uvicorn worker-count change, database migration or Redis protocol change.
- No Chinese Web or Chinese production deployment.
- No ASR, screenshot-answer, Companion, authentication, administration or commerce changes.

## Decisions

### Use a dedicated bounded executor with an async SSE bridge

The route will capture receipt time before returning the response, then an async generator will submit one producer to a small dedicated `ThreadPoolExecutor`. The producer iterates the existing synchronous service generator unchanged and hands serialized frames to a bounded `asyncio.Queue` through thread-safe loop callbacks. The consumer yields frames in order and cancels/releases resources on disconnect.

This isolates quick answer from Starlette's shared sync-iterator pool while retaining the proven synchronous Chat Service and provider client. Rewriting Chat Service and the provider gateway as fully async was rejected because it is a broad semantic and lifecycle change. Adding Uvicorn workers was rejected because in-process realtime state is not yet fully multi-process safe.

### Bound both execution and delivery

Executor workers and pending admissions will be fixed settings with conservative defaults. Each stream uses a small bounded event queue; producer handoff blocks through `run_coroutine_threadsafe` when the browser is slower than generation, creating bounded backpressure rather than unbounded memory growth. Saturation returns a safe 503 before answer generation and before billing reservation.

An unbounded executor queue was rejected because bursts could turn latency into memory growth. Dropping answer chunks was rejected because it changes answer content.

### Extend the existing timing envelope

Route receipt, executor submission and generator-start timestamps will be added to the existing optional timing object. Older Web clients ignore the fields, and the acknowledgement remains best effort. Timing contains no content.

Inferring the missing interval by subtracting client and server elapsed durations was rejected as the permanent solution because it cannot identify executor admission directly.

### Bypass coalescing only for first non-empty Global output

The Global Web will immediately apply the first non-empty chunk for each task. Subsequent chunks retain the existing 100ms coalescing window to bound React work. Domestic Web remains unchanged during the pilot.

## Risks / Trade-offs

- [A dedicated pool duplicates thread resources] → Use a small fixed pool, close it during application shutdown and expose content-free saturation counters.
- [A disconnected browser can leave a producer running briefly] → Propagate cancellation, stop queue delivery and rely on existing task cancellation/timeout behavior.
- [Bounded delivery can block a producer] → Keep the queue large enough for normal burst output and preserve ordering rather than dropping content.
- [Shared Backend source means a future domestic build includes the code] → Do not deploy Chinese production until Global evidence and domestic regression tests pass; retain a configuration kill switch if needed.
- [Global traffic may be too small for strong latency statistics] → Verify structural isolation deterministically and report production samples without overstating p95 confidence.

## Migration Plan

1. Capture the current Global Backend/Web images, release path, health and active-session state.
2. Add failing executor, timing, cancellation, saturation and first-chunk rendering tests.
3. Implement the bounded executor bridge and Global first-chunk rendering behavior.
4. Run focused and full Backend/Global Web tests, typecheck/build, privacy checks and strict OpenSpec validation; run relevant domestic regressions without deploying them.
5. When Global has no active interview workload, retain rollback tags and replace only Global Backend/Web.
6. Verify Global health, login/API route, live-answer status, build manifest, errors and stage metrics; verify Chinese health without changing it.
7. Roll back only Global Backend/Web if health, billing, answer behavior or error rate regresses.

## Open Questions

None for the isolated pilot. Domestic rollout remains a separate explicit approval after Global acceptance.
