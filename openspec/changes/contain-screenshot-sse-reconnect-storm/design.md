## Context

The 2026-09-03 incident began when one desktop device repeatedly opened the screenshot capture-request SSE route. The server recorded 11,748 completed screenshot streams in a fifty-minute sample, while ordinary API latency rose from seconds to minutes and `/api/v1/web/state` reached roughly 1,459 seconds. The existing 1.2.13 companion preserves one stream across eligible capture-state transitions, but legacy or faulty clients remain deployed.

The Backend currently validates each stream binding, creates an independent generator, and submits Redis `XREAD` work to the realtime event-wait executor. It has no server-side per-device ownership or global admission cap. Screenshot and realtime-session stream waits share the same executor, and the application has one Uvicorn worker because some runtime state is still process-local.

## Goals / Non-Goals

**Goals:**

- Contain a legacy or faulty device before duplicate screenshot streams consume blocking waits or control executor capacity.
- Guarantee at most one admitted screenshot stream for a device while preserving reconnect and pending-request replay.
- Bound global screenshot stream work and isolate it from transcript/session streams.
- Preserve current API paths, screenshot delivery, answer generation, billing, audio, ASR, subtitle, and UI behavior.
- Make overload visible without logging user content or raw device identifiers.

**Non-Goals:**

- No ASR, VAD, audio, subtitle, prompt, answer, vision-model, billing, Web, Admin, or Desktop behavior changes.
- No Uvicorn worker increase or runtime-state migration.
- No IP-based blocking, permanent device bans, new infrastructure, or destructive Redis migration.

## Decisions

### 1. Admit by device before binding work and retain a lease for the response lifetime

An application-scoped coordinator acquires a provisional lease keyed by `device_id` before synchronous binding validation. Only the lease owner may enter binding lookup and event waiting. The lease remains active until the StreamingResponse generator exits, and release is token-checked and idempotent.

This prevents identical valid requests from repeatedly entering the control executor. A device-only provisional key avoids storing the manual code. No binding secret or raw identifier is exported by diagnostics.

Alternative: admit after binding validation. Rejected because a reconnect storm would still amplify binding work. Alternative: limit by IP in Nginx. Rejected because NAT could group unrelated users and the application already has a stable device identity.

### 2. Reject duplicates and rapid sequential reconnects with legacy-compatible bounded backoff

While a device lease exists, duplicate stream attempts receive a structured HTTP 409 response with `Retry-After: 5` and `retryAfterMs=5000`. A short token-bucket window also limits sequential reconnects after a stream closes. Existing companions already treat non-success stream responses as failures and wait at least five seconds before retrying.

The first valid connection is never delayed. No 429 response or permanent ban is introduced. A newly registered device generation can reconnect after the old generator releases; cursor and pending lookup recover missed work.

Alternative: always replace the old connection. Rejected because a faulty client could continually supersede healthy work and still create a churn storm.

### 3. Give screenshot waits a dedicated executor and bounded admission

Screenshot `XREAD` waits use a dedicated `RealtimeEventWaitExecutor` configured independently from realtime transcript/session waits. The coordinator caps active screenshot streams globally; denied requests never submit blocking work. The global cap bounds the executor's otherwise unbounded internal queue.

Alternative: enlarge the existing shared pool. Rejected because it increases resource consumption without preventing starvation. Alternative: migrate immediately to `redis.asyncio`. Deferred because it changes the broader realtime repository and is unnecessary for containment.

### 4. Preserve replay and billing semantics

After admission and binding validation, the existing stream startup order remains: query the pending capture request, establish the current event cursor, emit pending work if present, then consume incremental events. Rejected duplicate connections never claim, upload, generate an answer, or bill. A reconnect therefore cannot lose a requested screenshot and cannot duplicate a charge.

### 5. Expose only aggregate diagnostics

Realtime metrics add aggregate screenshot admission data: active, maximum active, accepted, duplicate denied, reconnect-rate denied, global-cap denied, released, and the dedicated wait-executor configuration. No manual code, IP, screenshot, transcript, question, answer, or raw device ID is included.

## Risks / Trade-offs

- [A stale connection temporarily blocks a legitimate reconnect] → disconnect checks run at the existing one-second event-wait cadence; the client receives a five-second backoff and retries, while pending/cursor replay prevents loss.
- [A false duplicate decision delays screenshot notification] → ownership is scoped only to the same stable device ID and lease release is guaranteed in the generator `finally`; regression tests cover disconnect and reacquisition.
- [Sequential connect failures bypass a simple active lease] → a bounded per-device attempt window applies after releases and is pruned by monotonic time.
- [A global cap is too low for future growth] → make it configurable, default above current production concurrency, and expose saturation counts before tuning.
- [Legacy clients ignore Retry-After] → their existing failure policy still waits at least five seconds; server admission remains O(1) and does not schedule Redis waits.

## Migration Plan

1. Record current Git commit and Backend image/container identity as the rollback baseline.
2. Add coordinator, dedicated executor, aggregate metrics, and synthetic regression/storm tests with feature defaults enabled.
3. Run focused and full Backend tests plus a synthetic abusive-device load test while verifying audio/subtitle, quick-answer, screenshot, and billing regressions.
4. Build a candidate Backend image without replacing production.
5. Poll production until active interviews and active audio publishers are both zero; do not switch while either is nonzero.
6. Tag the current Backend image for rollback, replace only Backend, and verify health, Web state, binding, screenshot, and metrics.
7. Observe ordinary API P95/P99, 5xx, active screenshot streams, duplicate denials, executor saturation, ASR errors, and realtime delivery for at least 30 minutes.
8. Roll back immediately if screenshot delivery, audio, subtitles, answers, billing, or latency gates regress; Redis and PostgreSQL require no rollback.

## Open Questions

None. Initial safe defaults are one stream per device, five-second duplicate backoff, a configurable global active cap, and a dedicated bounded screenshot wait pool; load tests may lower resource usage but must not relax correctness gates.
