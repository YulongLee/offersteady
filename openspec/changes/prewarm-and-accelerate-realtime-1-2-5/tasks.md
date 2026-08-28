## 1. Warm Preparation Ownership

- [x] 1.1 Add regression tests for one-shot local media transfer, stale-source rejection, cleanup, and no preparation publication.
- [x] 1.2 Implement transferable local-source ownership and consume healthy warmed streams in the live publisher with per-source fallback.
- [x] 1.3 Update companion lifecycle orchestration so preparing-to-live promotes warmed sources without duplicate listeners or device reopen.

## 2. Backend Readiness

- [x] 2.1 Add backend tests for preparing-session dual-channel prewarm, non-blocking live start, no pre-live billing/audio acceptance, and warmup refresh/cleanup.
- [x] 2.2 Schedule and expose best-effort provider readiness from the authoritative preparing binding while retaining live-only publisher authorization.

## 3. Endpointing And Transcript Continuity

- [x] 3.1 Add desktop endpointing regressions for 350 ms system tail, 480 ms microphone tail, residual noise, short pauses, and single terminal emission.
- [x] 3.2 Implement source-aware endpoint tails and preserve terminal-priority delivery and generation identity.
- [x] 3.3 Add Web/backend regressions for visible provisional text, bounded committing/incomplete state, and late-generation isolation.
- [x] 3.4 Implement monotonic provisional/final handling and bounded recovery without changing the approved layout.

## 4. Diagnostics And Version

- [x] 4.1 Extend content-free runtime diagnostics for preparation-ready, warm promotion/open fallback, first frame/ACK, terminal, provider final, and visible-state boundaries.
- [x] 4.2 Increment companion/package metadata to 1.2.5 while preserving identity, endpoints, protocol, and approved icon/layout.

## 5. Verification And Local Acceptance

- [x] 5.1 Run focused desktop, backend, Web, and protocol regressions for the changed paths.
- [x] 5.2 Run workspace typechecks/builds, AI eval validation when applicable, and strict OpenSpec validation.
- [x] 5.3 Build and verify the signed macOS arm64 1.2.5 application, retaining 1.2.4 as a recoverable rollback.
- [x] 5.4 Install and open the local 1.2.5 companion for user physical acceptance without deploying Backend or Web changes.
