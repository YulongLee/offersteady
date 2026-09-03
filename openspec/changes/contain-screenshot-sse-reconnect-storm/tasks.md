## 1. Baseline and tests first

- [x] 1.1 Record the current Git and production Backend image/container baseline without changing production
- [x] 1.2 Add coordinator tests for per-device ownership, duplicate denial, release/reacquisition, sequential reconnect rate, global capacity, and aggregate diagnostics
- [x] 1.3 Add route and lifecycle regression tests proving denied streams avoid binding/event waits and admitted streams release ownership
- [x] 1.4 Add replay and product regression coverage for pending screenshots, cursor delivery, answer generation, billing, and realtime isolation

## 2. Bounded screenshot stream runtime

- [x] 2.1 Implement an application-scoped screenshot stream admission coordinator with token-safe idempotent leases
- [x] 2.2 Enforce per-device ownership, sequential reconnect backoff, and configurable global capacity before binding lookup
- [x] 2.3 Release stream ownership on disconnect, cancellation, validation failure, and application shutdown
- [x] 2.4 Add a dedicated screenshot event-wait executor and route screenshot Redis blocking waits through it

## 3. Compatibility and observability

- [x] 3.1 Return a structured legacy-compatible retry response and `Retry-After` header for denied screenshot streams
- [x] 3.2 Expose aggregate screenshot admission and dedicated executor diagnostics without user content or raw identifiers
- [x] 3.3 Preserve existing API paths, pending lookup, event cursor, screenshot processing, and exactly-once billing behavior

## 4. Verification

- [x] 4.1 Run focused coordinator, route, realtime, screenshot, billing, and capacity tests
- [x] 4.2 Run the full Backend regression suite and strict OpenSpec validation
- [x] 4.3 Run a synthetic reconnect-storm profile and verify bounded active work, ordinary API P95 <= 500 ms, P99 <= 1 s, and zero 5xx

## 5. Safe production rollout

- [ ] 5.1 Build a candidate Backend image and retain the recorded baseline image and runtime data
- [ ] 5.2 Poll production until active interviews and active audio publishers are both zero without changing live traffic
- [ ] 5.3 Replace only Backend, run health/Web-state/binding/screenshot/realtime smoke tests, and verify other containers remain unchanged
- [ ] 5.4 Observe production metrics for at least 30 minutes and roll back immediately on correctness or performance regression
