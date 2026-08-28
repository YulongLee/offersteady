## 1. Readiness Model And Tests

- [x] 1.1 Add desktop regressions for track-open versus fresh-signal readiness, 120-second expiry, and lifecycle invalidation.
- [x] 1.2 Add warm-handoff regressions proving that only healthy fresh sources are promoted and no preparation PCM is published.
- [x] 1.3 Add quiet-system-speech regressions for bounded startup, pre-speech retention, and true-silence suppression.

## 2. Desktop Sound Check And Capture

- [x] 2.1 Implement source-specific local readiness evidence and invalidation in the preparation monitor and handoff.
- [x] 2.2 Add explicit microphone/computer-output sound-check status and retry guidance within the approved companion layout.
- [x] 2.3 Revalidate readiness at preparing-to-live transition and independently reopen only stale sources.
- [x] 2.4 Harden system VAD noise learning and first-speech buffering without changing terminal delivery semantics.

## 3. Compatible Entry Gate

- [x] 3.1 Add Web preparation regressions for audio-assisted gating, stale-source guidance, and permission-free manual entry.
- [x] 3.2 Implement the compatible preparation start gate using safe source-health/readiness state without changing the approved live layout.

## 4. Version And Verification

- [x] 4.1 Increment companion metadata to 1.2.6 and add release assertions while preserving identity, icon, endpoints, and protocol.
- [x] 4.2 Run focused and full desktop/Web tests, builds/typechecks, and strict OpenSpec validation.
- [x] 4.3 Build and verify the signed macOS arm64 1.2.6 app while retaining a recoverable 1.2.5 backup.
- [x] 4.4 Install and reopen the local 1.2.6 companion for user acceptance, clearly separating local desktop evidence from undeployed production Web/Backend behavior.
