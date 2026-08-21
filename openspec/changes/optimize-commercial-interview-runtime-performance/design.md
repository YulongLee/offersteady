## Context

The production runtime already separates microphone/system PCM, uses one authenticated desktop WebSocket, keeps persistent ASR provider sessions, publishes ordered Redis session events, and streams manual answers over dedicated SSE. Screenshot capture requests are pushed to the desktop through the same event store and the image is now delivered inline to the vision model without OSS persistence.

Three bottlenecks remain. The vision gateway uses a non-streaming completion so the browser stays blank until the full answer finishes. Session SSE loops perform an empty Redis cursor read every 100 ms per connection. Audio frames are queued per source, but each source worker still waits briefly for a provider partial after each append. In addition, chat and screenshot task repositories are process-local, preventing reliable recovery across backend restarts and multi-worker operation. Existing telemetry records server stages but does not correlate browser intent and render completion.

The change must preserve explicit user control, current prompts, selected-material behavior, billing idempotency, old desktop compatibility, and privacy defaults. Raw PCM and screenshot bytes remain memory-only and are never written to telemetry or the task store.

## Goals / Non-Goals

**Goals:**

- Reduce screenshot time-to-first-visible-answer without shortening the final answer.
- Remove fixed-interval empty event reads while preserving ordered resume semantics.
- Keep audio append work independent from provider partial delivery and retain final transcript correctness.
- Make active task metadata visible across backend processes and recover terminal/interrupted state after restart.
- Prefetch detail retrieval without delaying the quick-answer first token.
- Measure client intent-to-render latency with payload-free correlated timestamps.

**Non-Goals:**

- No ASR, chat, vision, embedding, or reranker model replacement.
- No prompt, price, point rate, speaker-role, material-selection, or public layout change.
- No storage of raw audio or screenshot bytes in Redis/PostgreSQL/OSS.
- No automatic answer generation from speech transcripts.
- No requirement to resume an in-flight provider call after process death; interrupted work becomes safely retryable.

## Decisions

### Stream vision output through the existing screenshot task lifecycle

Extend the vision gateway with an incremental iterator that yields monotonic text snapshots/chunks and a final usage result. The screenshot service persists each throttled task revision and calls the existing transition publisher. The browser receives partial screenshot tasks through the unified session SSE and uses the same monotonic answer reducer already used for manual answers. Terminal events flush immediately; progress publication is coalesced to avoid one Redis event per provider token.

Alternative: add a second dedicated screenshot SSE. Rejected because the capture request already has a reliable session event channel and a second stream would recreate the state-race problem previously removed.

### Use Redis JSON task repositories with bounded TTL

Production chat and screenshot repositories use Redis keys and sorted indexes scoped by owner/session, while unit tests retain deterministic in-memory adapters. Writes are whole-record JSON replacements guarded by a short per-record Redis lock and monotonic revision/update checks. Upload bytes stay in the current process only; persisted upload metadata is marked interrupted if its bytes disappear. Queued/generating tasks older than a configured threshold become failed/retryable when read after restart.

Alternative: add PostgreSQL tables immediately. Rejected because these are transient live tasks with short retention, Redis is already required by the production realtime path, and no durable user content expansion is needed.

### Replace cursor polling with blocking Redis Stream reads

Add a repository wait operation backed by `XREAD BLOCK` starting at the stream entry corresponding to the current cursor. The route performs the blocking call in a worker thread with a bounded timeout so disconnect, lease validation, and keepalive checks continue. In-memory repositories use a condition variable. Existing snapshot and cursor-expiry behavior remains the recovery authority.

Alternative: Redis Pub/Sub. Rejected because Pub/Sub cannot replay missed events and would require a second reconciliation channel.

### Make non-final ASR append non-blocking

The persistent provider receiver remains the only reader. For non-final frames the source worker appends PCM and immediately returns the latest available transcript snapshot without waiting for a new provider event. The next source frame or provider notification publishes newer partial state. Final frames still commit and wait for the provider terminal event with the current timeout and retry behavior. Per-source ordering and bounded queues remain unchanged.

Alternative: a new standalone media gateway. Rejected as unnecessary architecture expansion for the current scale.

### Prefetch detail retrieval without changing first-token behavior

Start retrieval for the raw explicit question in a bounded executor immediately before quick generation. If question normalization preserves the retrieval key, reuse the future; otherwise run retrieval for the normalized question. Retrieval failure falls back to the existing synchronous path and never interrupts the quick answer stream.

Alternative: run quick and detail model generation concurrently. Rejected because the detailed prompt intentionally anchors to the completed quick answer.

### Correlate timing stages with opaque trace identifiers

The web creates an opaque action trace ID and intent timestamp for quick/screenshot actions. Desktop and backend propagate timestamps for request push, capture, compression, upload acceptance, model first text, completion, event publication, and browser render. A small authenticated acknowledgement endpoint records only identifiers, stage durations, status, source type, and safe error codes. It rejects content fields and applies bounded retention/sampling.

Alternative: log full request objects for debugging. Rejected because questions, answers, screenshots, and transcripts are sensitive.

## Risks / Trade-offs

- [Provider streaming formats vary] → Keep the gateway adapter-specific parser, a non-streaming fallback flag, and final-response validation.
- [Redis task JSON replacement can race] → Enforce monotonic revision/update time and short record locks; terminal state cannot regress.
- [Blocking reads occupy worker threads] → Bound wait duration and use the existing thread offload; later migration to an async Redis client remains possible.
- [Non-final ASR results may appear on the next 100 ms frame] → Final correctness is unchanged and interim publication is monotonic; retain a feature flag for the previous 30 ms wait.
- [Prefetched retrieval may use an unnormalized question] → Reuse only when normalization is equivalent, otherwise recompute.
- [More timing events increase storage] → Store only sampled compact records with TTL and aggregate them before admin reporting.
- [Backend restart cannot resume provider calls] → Mark stale tasks retryable, release billing reservations through existing idempotent recovery, and never show them indefinitely as processing.

## Migration Plan

1. Deploy backend support with Redis repositories, blocking reads, streaming-compatible screenshot events, and compatibility flags disabled where needed.
2. Deploy web support for screenshot partial reconciliation and render acknowledgements; old web/desktop clients continue using terminal events and fallback endpoints.
3. Enable blocking reads and ASR non-blocking partial append, then observe queue depth, reconnects, final transcript latency, and error rate.
4. Enable screenshot provider streaming after a synthetic production probe confirms provider compatibility.
5. Compare pre/post p50/p95 for transcript render, quick first token, screenshot first text, full completion, and failure rate.
6. Roll back individual feature flags or the affected web/backend image if error rate rises; no schema rollback is needed.

## Open Questions

None. Provider streaming capability is probed at runtime and falls back to the existing complete-response path.
