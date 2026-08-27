## 1. Regression Baseline

- [x] 1.1 Add desktop regressions for prompt first speech, system residual-noise release, short-pause resume, and last-meaningful-speech diagnostics.
- [x] 1.2 Add backend regressions for bounded committing completion, following-utterance admission, and content-free stop-stage aggregation.
- [x] 1.3 Add Web regressions for one leader-owned stream, initial-snapshot recovery, retained fallback backoff, and bounded confirming presentation.

## 2. Desktop Endpointing

- [x] 2.1 Implement system peak-relative release and a bounded last-meaningful-speech deadline without changing silence readiness.
- [x] 2.2 Propagate content-free last-meaningful-speech and terminal timing fields through protocol-v2 desktop diagnostics.

## 3. Backend Terminal And Delivery

- [x] 3.1 Keep terminal admission, provider confirmation, watchdog recovery, and later utterance ordering independently bounded per source.
- [x] 3.2 Expose committing lifecycle and aggregate last-meaningful-speech-to-terminal stages without persisting audio or transcript content.
- [x] 3.3 Make session-stream initial delivery prompt and preserve terminal events plus reconnect cursor correctness.

## 4. Web Lifecycle

- [x] 4.1 Stabilize initial SSE ownership and reconnect/fallback behavior so only a parsed stream snapshot resets recovery.
- [x] 4.2 Project speaking, transcribing, bounded confirming, final, and incomplete states in the existing transcript layout.

## 5. Version And Documentation

- [x] 5.1 Increment companion and lockfile metadata to 1.2.3 while preserving icons, layout, bundle identity, signing configuration, and production defaults.
- [x] 5.2 Update privacy-safe realtime eval fixtures, runtime documentation, and local 1.2.3 release notes.

## 6. Verification And Local Acceptance

- [x] 6.1 Run focused and full backend, desktop, Web, protocol, and eval tests plus typechecks, builds, and strict OpenSpec validation.
- [x] 6.2 Build and verify the local macOS 1.2.3 package and signing identity without changing production services or manifests.
- [x] 6.3 Start the exact local 1.2.3 companion artifact and record bounded authorized live-test metrics for first-visible and stop-to-terminal acceptance, including the observed microphone residual-noise exception accepted for rollout.

## 7. Cross-platform Production Rollout

- [x] 7.1 Verify shared endpointing/protocol code and regressions cover macOS ARM64, macOS Intel x64, and Windows x64 without platform-only forks.
- [x] 7.2 Build and inspect the Windows x64 installer and both macOS architecture artifacts; require Developer ID/notarization/staple/Gatekeeper for macOS and truthful unsigned metadata for Windows.
- [x] 7.3 Publish the three 1.2.3 artifacts atomically, deploy compatible Backend/Web changes, and verify production health, manifest versions, ranged downloads, hashes, and rollback reference.
