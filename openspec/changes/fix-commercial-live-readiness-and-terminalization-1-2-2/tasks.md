## 1. Regression Baseline

- [x] 1.1 Add backend regressions for publisher-attachment rewarm after process restart and same-source single-flight behavior.
- [x] 1.2 Add backend regressions for committing watchdog coverage, complete-utterance retry, and bounded in-memory buffer cleanup.
- [x] 1.3 Add desktop/Web regressions for independent microphone/system readiness without changing the existing layout.

## 2. Authoritative Readiness

- [x] 2.1 Rewarm provider sources idempotently when an authenticated publisher attaches to an already-live capturing interview.
- [x] 2.2 Publish per-source capture and provider readiness through backward-compatible runtime/device-status fields.
- [x] 2.3 Project preparing, ready, and degraded source state into the existing Web status presentation and complete content-free readiness telemetry.

## 3. Bounded Terminal Recovery

- [x] 3.1 Add a capped, source-segment in-memory PCM replay buffer with deterministic cleanup and aggregate diagnostics.
- [x] 3.2 Keep terminal turns in `committing` supervision until final/incomplete and prevent tail-only provider retries.
- [x] 3.3 Preserve subsequent source audio under slow completion and publish one monotonic incomplete recovery at the deadline.

## 4. Companion 1.2.2

- [x] 4.1 Increment desktop package and release metadata to 1.2.2 while preserving layout, icons, signing identity, and production defaults.
- [x] 4.2 Update privacy-safe realtime eval fixtures and operational documentation for readiness and terminal recovery.

## 5. Verification And Local Acceptance

- [x] 5.1 Run focused backend, desktop, Web, protocol, and AI evaluation regressions plus OpenSpec strict validation.
- [ ] 5.2 Run affected full tests, typechecks, production builds, and a bounded local soak with truthful latency results.
- [x] 5.3 Build and verify the local macOS 1.2.2 companion, start it without mutating production, and leave production services unchanged for user acceptance.
