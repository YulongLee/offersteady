## 1. Baseline and instrumentation

- [x] 1.1 Record Git commit `dfc3ca8` and production image/container identity as the rollback baseline
- [x] 1.2 Add content-free counters for global snapshot writes, entity writes, duplicate query reuse and control executor saturation

## 2. Incremental realtime state

- [x] 2.1 Add versioned Redis entity storage for desktop devices, manual-code lookup, web heartbeats and active live page lookup
- [x] 2.2 Overlay entity state on legacy snapshot recovery and idempotently seed missing entity state from the legacy snapshot
- [x] 2.3 Move desktop heartbeat persistence to an entity-only pipeline without a global snapshot rewrite
- [x] 2.4 Move web heartbeat and live-page claim persistence to entity-only updates while preserving lease generation semantics
- [x] 2.5 Persist only the changed session activity field on incremental transcript/event updates

## 3. Retry containment and event-loop isolation

- [x] 3.1 Add bounded sub-second reuse for identical active-connection and invalid binding lookups with semantic invalidation
- [x] 3.2 Preserve legacy status codes while returning bounded retry advice and sampling repeated invalid-binding diagnostics
- [x] 3.3 Route short synchronous control operations through an isolated bounded executor without moving ASR or WebSocket audio work

## 4. Verification

- [x] 4.1 Add legacy recovery, newer-entity overlay, heartbeat write-amplification and activity monotonicity tests
- [x] 4.2 Add duplicate/invalid request storm and executor isolation regression tests
- [x] 4.3 Run focused backend tests, full backend regression, OpenSpec strict validation and a synthetic control-plane load profile
- [x] 4.4 Verify ASR, subtitle monotonicity, quick answer, screenshot answer and billing regression coverage remains green

## 5. Production rollout and rollback readiness

- [x] 5.1 Build a candidate backend image and preserve the baseline image without replacing Web, Admin, Desktop, PostgreSQL or Redis
- [x] 5.2 Confirm active interviews and audio streams are zero before switching production traffic
- [x] 5.3 Deploy the candidate, verify health and core APIs, and observe API P95/P99, CPU, Redis traffic, 5xx and realtime errors
- [x] 5.4 Keep the baseline image and legacy Redis state available; roll back immediately if any correctness or performance gate fails
