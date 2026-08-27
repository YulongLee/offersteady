## 1. Regression Coverage

- [ ] 1.1 Add a failed-first-open then successful system recovery regression
- [ ] 1.2 Add stop/race and single-flight resource cleanup regressions
- [ ] 1.4 Add a transport-replacement regression proving healthy media runtimes are not stopped
- [x] 1.5 Add microphone headset-removal fallback and explicit-device-selection policy regressions
- [x] 1.6 Add Desktop and Backend regressions for an unacknowledged terminal covered by a resume offset
- [x] 1.7 Add a microphone regression proving overlapping track-ended and device-change recovery retries until a runtime is attached
- [x] 1.3 Add a diagnostic regression proving resend cannot lower last-sent sequence

## 2. Runtime Repair

- [x] 2.1 Move system recovery ownership to a publisher-level bounded retry supervisor
- [x] 2.2 Preserve publisher, microphone runtime, system sequence, and terminal ordering during retry
- [x] 2.3 Add metadata-only recovery attempt and outcome diagnostics
- [x] 2.4 Fall back to the default microphone with bounded retries when a headset input disappears
- [x] 2.5 Retain and re-admit terminal frames until explicit terminal acknowledgement
- [x] 2.6 Require an attached microphone runtime before an overlapping device-switch recovery is considered converged

## 3. Release and Verification

- [x] 3.1 Increment companion release metadata to 1.1.8
- [x] 3.2 Run focused and full Desktop tests, typecheck, builds, and strict OpenSpec validation
- [x] 3.3 Build and install the local macOS companion, then start it for physical acceptance
- [ ] 3.4 Complete physical headset-removal acceptance with zero publisher reset and automatic system capture recovery
