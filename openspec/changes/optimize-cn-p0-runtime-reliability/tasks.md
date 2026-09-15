## 1. Resource observability

- [x] 1.1 Implement container RSS and host memory measurements with explicit API fields and labels.
- [x] 1.2 Add focused tests for unlimited and limited cgroup environments and dashboard serialization.

## 2. Interview finalization

- [x] 2.1 Trace end, cancel, and idle-expiry paths and verify idempotent session resource finalization across the existing lifecycle.
- [x] 2.2 Verify cleanup counters and regression coverage for provider, transport, executor, and buffer release.

## 3. Quick-answer latency

- [x] 3.1 Trace click-to-render boundaries and remove avoidable pre-first-display work without changing answer content.
- [x] 3.2 Add quick-answer latency regression tests, including provider failure cleanup and optional timing compatibility.

## 4. Verification and release

- [x] 4.1 Run focused backend/frontend tests, OpenSpec validation, and build the tagged production images.
- [x] 4.2 Deploy the backend and web with rollback images retained and run health, metric, quick-answer, and cleanup smoke checks.
