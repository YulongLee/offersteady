## 1. Binding lifecycle implementation

- [x] 1.1 Add regression tests for unchanged capture state, duplicate binding notifications, binding replacement and missing binding.
- [x] 1.2 Expose a typed renderer-to-main binding lifecycle IPC bridge.
- [x] 1.3 Publish authoritative binding identity from the existing single-flight pairing poll.
- [x] 1.4 Update the main-process screenshot stream owner to restart a suspended stream on valid binding notification without creating duplicate owners.

## 2. Release verification

- [x] 2.1 Bump Companion to 1.2.15 and verify package metadata.
- [x] 2.2 Run focused regression tests, full desktop tests, type checks and builds.
- [x] 2.3 Build and verify macOS arm64, macOS x64 and Windows x64 artifacts.
- [x] 2.4 Validate the OpenSpec change in strict mode.

## 3. Safe production rollout

- [x] 3.1 Publish immutable 1.2.15 artifacts and update only the domestic release manifest.
- [ ] 3.2 Confirm zero active interviews immediately before deployment.
- [ ] 3.3 Deploy the domestic backend manifest update and verify health, downloads and initial error/latency metrics.
