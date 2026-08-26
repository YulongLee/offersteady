## 1. Regression Coverage

- [x] 1.1 Add device-selection reconciliation tests for retained, removed, and rapidly changing macOS microphone routes.
- [x] 1.2 Add publisher tests proving a microphone switch preserves the system runtime, shared transport, and monotonic channel sequence.
- [x] 1.3 Add transport tests proving duplicate sequence-gap responses cannot amplify sends inside cooldown and still escalate after the bounded retry budget.
- [x] 1.4 Add recovery tests proving a connected silent replacement publisher remains ready until media exists.

## 2. Runtime Implementation

- [x] 2.1 Debounce device-change refresh and preserve a still-available explicit microphone selection.
- [x] 2.2 Decouple microphone selection from publisher ownership and implement serialized source-only microphone switching.
- [x] 2.3 Apply gap cooldown and retry checks before clearing in-flight state, preserving bounded retransmission.
- [x] 2.4 Keep control-plane-ready replacement publishers alive during silence and retain bounded first-frame acknowledgement.

## 3. Companion Release

- [x] 3.1 Increment desktop companion patch version from 1.1.5 to 1.1.6 across package and release metadata.
- [x] 3.2 Build and verify macOS arm64/x64 and Windows x64 1.1.6 artifacts with immutable checksums.

## 4. Verification and Production Rollout

- [x] 4.1 Run focused hot-switch regressions, desktop type checks, full desktop tests, and OpenSpec strict validation.
- [x] 4.2 Run affected workspace tests and production packaging checks without persisting audio or transcript content.
- [ ] 4.3 Commit and push the tested source revision while preserving the 1.1.5 manifest as rollback.
- [ ] 4.4 Publish the verified 1.1.6 companion manifests and verify production health and download checksums.
- [ ] 4.5 Perform metadata-only production validation and leave physical headset-removal acceptance pending for the user.
