## Why

Recent Chinese production traces show browser click-to-first-render latency of 2.74–6.81 seconds even though the model's raw first token remains 0.61–0.97 seconds. The largest unbounded interval is before the synchronous answer iterator begins, so OfferSteady needs isolated stream admission and complete entry telemetry before this optimization is considered for Chinese production.

## What Changes

- Record a server receipt timestamp before `StreamingResponse` hands work to its iterator so route admission delay is measurable separately from model and prompt work.
- Run live-answer production through a dedicated bounded executor and an async SSE bridge rather than the shared framework thread pool.
- Deliver the first non-empty answer update immediately in the Global Web while preserving bounded coalescing for later chunks.
- Preserve the current model, prompts, normalization, RAG evidence, answer ordering, billing reservation, cancellation, persistence, privacy and API compatibility.
- Pilot and deploy the change only on the independent Global production stack; do not build, restart or modify Chinese production services.

## Capabilities

### New Capabilities

- `bounded-live-answer-stream-admission`: Provides bounded, observable and isolated admission from an accepted live-answer HTTP request to the existing synchronous answer generator and first SSE chunk.

### Modified Capabilities

<!-- No main-spec requirement changes. Existing quick-answer behavior remains unchanged. -->

## Impact

- Shared Backend live-answer route, executor lifecycle and privacy-safe runtime timing fields.
- Global Web first-chunk rendering and focused regression tests.
- Global-only Backend/Web deployment on `offersteady.com`, with the preceding Global release retained for rollback.
- No schema migration, provider change, prompt change, sensitive-data telemetry or Chinese production deployment.
