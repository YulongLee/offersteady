## 1. Baseline and regression protection

- [x] 1.1 Capture Global production release, active workload, health and rollback images without changing running services
- [x] 1.2 Add focused tests for bounded answer admission, ordered streaming, saturation, cancellation and privacy-safe entry timing
- [x] 1.3 Add a Global Web regression proving the first non-empty chunk bypasses follow-up coalescing while later chunks remain bounded

## 2. Backend stream admission

- [x] 2.1 Implement a lifecycle-managed dedicated bounded live-answer executor with ordered backpressure and diagnostics
- [x] 2.2 Bridge the existing synchronous answer iterator through the dedicated executor without changing Chat Service semantics
- [x] 2.3 Add route receipt, executor admission and generator start fields to the existing content-free timing envelope and metrics

## 3. Global first-visible rendering

- [x] 3.1 Apply the first non-empty Global answer update immediately and retain the current coalescing window for later updates
- [x] 3.2 Keep the Chinese Web source and deployed Chinese services unchanged

## 4. Verification and Global-only release

- [x] 4.1 Run focused and full Backend and Global Web tests, typechecks, builds, privacy checks and relevant domestic regressions
- [x] 4.2 Run strict OpenSpec validation and review the scoped diff for unrelated or user-owned changes
- [x] 4.3 When Global has no active interview workload, retain rollback images and deploy only Global Backend/Web
- [x] 4.4 Verify Global health, answer status, build metadata, logs and stage telemetry; verify Chinese production health without deploying it
