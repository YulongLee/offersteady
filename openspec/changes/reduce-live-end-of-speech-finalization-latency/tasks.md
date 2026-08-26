## 1. Regression Coverage

- [x] 1.1 Add desktop segmenter tests for residual-noise release, tail resume, quiet speech, and bounded finalization latency.
- [x] 1.2 Add backend tests proving suppressed and superseded partials emit terminal events without answer, context, usage, or billing side effects.
- [x] 1.3 Update web tests for the four-second stale-partial presentation boundary.

## 2. Runtime Implementation

- [x] 2.1 Implement peak-relative microphone release and reduce the commercial microphone tail to 500 ms while preserving system-channel behavior.
- [x] 2.2 Publish a monotonic terminal transcript event when a final result is suppressed and terminalize a prior segment superseded on the same source.
- [x] 2.3 Enable the four-second source watchdog in the production Compose configuration and align the web stale guard.

## 3. Companion Release

- [x] 3.1 Increment the desktop companion patch version from 1.1.4 to 1.1.5 across package and release metadata.
- [x] 3.2 Build and verify macOS arm64/x64 and Windows x64 1.1.5 release artifacts with immutable checksums.

## 4. Verification and Production Rollout

- [x] 4.1 Run focused desktop, backend, and web regressions plus OpenSpec strict validation.
- [x] 4.2 Run affected workspace type checks, full tests, and production builds; record truthful results.
- [x] 4.3 Commit the tested source revision and preserve explicit backend, web, and companion rollback identifiers.
- [x] 4.4 Deploy backend then web, publish the verified companion manifests, and verify production health and configuration.
- [x] 4.5 Perform metadata-only production realtime validation and leave real speech acceptance pending for the user.
