## 1. Lifecycle model

- [x] 1.1 Define session lease signals, grace periods, and active/suspect/closing/closed transitions.
- [x] 1.2 Add configuration for watchdog interval, grace period, dry-run, and per-session buffer limits.

## 2. Unified cleanup

- [x] 2.1 Implement idempotent session cleanup coordinator with session-level locking.
- [x] 2.2 Route normal end, disconnect, heartbeat expiry, ASR failure, and admin termination through coordinator.
- [x] 2.3 Ensure persistent ASR stale sessions are eligible for lease-based cleanup.

## 3. Watchdog and metrics

- [x] 3.1 Add bounded background watchdog and graceful application shutdown.
- [x] 3.2 Expose reclamation counters, durations, resource counts, and RSS deltas.

## 4. Tests and release

- [ ] 4.1 Add regression tests for active silence, disconnect expiry, ASR failure, duplicate cleanup, and watchdog dry-run.
- [ ] 4.2 Run lint, typecheck, build, and backend test suite.
- [x] 4.3 Deploy to international environment only and verify health, active-session preservation, and reclamation metrics.
