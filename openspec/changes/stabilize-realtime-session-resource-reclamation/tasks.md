## 1. Lifecycle model

- [x] 1.1 Define session lease signals, grace periods, and active/suspect/closing/closed transitions.
- [x] 1.2 Add configuration for watchdog interval, grace period, dry-run, and per-session buffer limits.

## 2. Unified cleanup

- [x] 2.1 Implement idempotent session cleanup coordinator with session-level locking.
- [x] 2.2 Route normal end, disconnect, heartbeat expiry, ASR failure, and admin termination through coordinator.
- [x] 2.3 Ensure persistent ASR stale sessions are eligible for lease-based cleanup.
- [x] 2.4 Remove ended-session realtime Redis streams and process-local event state while preserving review transcripts.
- [x] 2.5 Fence late ASR/worker writes, keep concurrent cleanup serialized, and bound retired-session indexes.
- [x] 2.6 Sweep Redis runtime references that belong to already-ended database sessions.

## 3. Watchdog and metrics

- [x] 3.1 Add bounded background watchdog and graceful application shutdown.
- [x] 3.2 Expose reclamation counters, durations, resource counts, and RSS deltas.
- [x] 3.3 Reduce preparation-page control-plane polling to a 10-second cadence with single-flight and bounded failure backoff.
- [x] 3.4 Coalesce duplicate desktop heartbeat persistence on the server without requiring a companion upgrade.

## 4. Tests and release

- [x] 4.1 Add regression tests for active silence, disconnect expiry, ASR failure, duplicate cleanup, and watchdog dry-run.
- [x] 4.5 Add regression coverage for ended-session runtime stream cleanup and transcript preservation.
- [x] 4.6 Deploy the cleanup patch to domestic production only after confirming zero live interviews; verify backend health, public web state, and non-backend containers remain unchanged.
- [x] 4.4 Add web and desktop regression coverage for bounded polling cadence and run the affected workspace tests.
- [ ] 4.2 Run lint, typecheck, build, and backend test suite.
- [x] 4.3 Deploy to international environment only and verify health, active-session preservation, and reclamation metrics.
- [x] 4.7 Add and run backend regressions for late-write fencing, lock lifetime, orphan sweeping, and heartbeat coalescing.

Validation note: 28 targeted backend regressions pass, including late-write fencing, cleanup lock lifetime, orphan sweeping, heartbeat coalescing, and superseded-session runtime removal. OpenSpec strict validation and Python compilation pass. The full backend suite reports 595 passed, 21 skipped, 16 subtests passed, and five pre-existing baseline failures outside this change (production WeChat error-code expectation, runtime performance timing assertion, and three prompt-quality assertions); 4.2 remains open until those baseline failures are resolved.
