## 1. Baseline and configuration

- [x] 1.1 Add feature flags, TTLs, stale-task limits, event wait duration, streaming throttle, and telemetry sampling configuration with production-safe defaults.
- [x] 1.2 Add synthetic baseline tests for screenshot first text, session event wake latency, non-final ASR append, quick/detail timing, and task restart recovery.

## 2. Shared transient task persistence

- [x] 2.1 Implement Redis serialization helpers and a Redis-backed chat task repository with session indexes, TTL refresh, monotonic writes, and stale active-task recovery.
- [x] 2.2 Implement a Redis-backed screenshot repository for tasks, capture requests, and safe upload metadata without media bytes.
- [x] 2.3 Select Redis repositories in production dependency wiring while preserving in-memory test adapters and safe fallback rules.
- [x] 2.4 Add repository tests for restart visibility, terminal precedence, TTL/index cleanup, stale interruption, and sensitive-field exclusion.

## 3. Low-latency ordered event delivery

- [x] 3.1 Extend realtime repository ports with bounded wait-after-cursor semantics for Redis and in-memory implementations.
- [x] 3.2 Replace web and desktop session-event fixed polling loops with bounded blocking waits while retaining keepalive, lease validation, fallback, and cursor recovery.
- [x] 3.3 Add tests proving prompt wake-up, no-event timeout, reconnect resume, and old desktop fallback compatibility.

## 4. Realtime ASR and quick-answer pipeline

- [x] 4.1 Make non-final persistent ASR appends non-blocking behind a rollback flag while keeping final commit/timeout/retry behavior unchanged.
- [x] 4.2 Add ASR tests for ordered partial/final delivery, delayed provider output, queue bounds, cancellation, and no frame loss.
- [x] 4.3 Prefetch detailed retrieval during quick generation and safely recompute when normalization changes the retrieval key.
- [x] 4.4 Add chat tests/evals proving first-token behavior, selected-material grounding, complete quick/detail output, cancellation, billing idempotency, and retrieval fallback.

## 5. Streaming screenshot answers

- [x] 5.1 Add a streaming-capable vision gateway result protocol with provider parser, monotonic chunks, first-text timing, terminal usage, and complete-response fallback.
- [x] 5.2 Persist throttled screenshot progress revisions and publish them through the existing capture/session event lifecycle.
- [x] 5.3 Reconcile partial screenshot answers in the web workspace without changing button labels, answer ordering, cancellation, or screenshot-only evidence.
- [x] 5.4 Add backend, web, and AI eval coverage for first text before completion, final completeness, fallback, retry, cancellation, duplicate events, and billing.

## 6. Privacy-safe end-to-end telemetry

- [x] 6.1 Add allow-listed runtime timing schemas, storage with bounded retention, and an authenticated best-effort acknowledgement endpoint.
- [x] 6.2 Propagate opaque trace IDs and timing stages through quick answer, screenshot capture/upload/model/event, transcript events, and browser render acknowledgement.
- [x] 6.3 Add privacy tests proving telemetry rejects or omits content, media payloads, credentials, phone numbers, and filenames.

## 7. Verification and release

- [x] 7.1 Run focused backend, web, desktop, protocol, AI eval, typecheck, build, and synthetic performance tests after each affected stage.
- [x] 7.2 Run the complete repository regression suite and validate the OpenSpec change with strict mode.
- [x] 7.3 Document pre/post timing evidence, feature flags, rollback steps, and remaining physical-device acceptance requirements.
- [x] 7.4 Commit only scoped files, push main, deploy affected services without rebuilding unrelated services, and verify production health/logs/synthetic probes.
