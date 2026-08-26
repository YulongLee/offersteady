## 1. Regression Baseline

- [x] 1.1 Add a gateway concurrency regression proving microphone and system prewarm overlap while same-channel callers share one connection
- [x] 1.2 Add live-start regressions for both-ready, timeout, failure, and lazy fallback behavior
- [x] 1.3 Add first-payload and first-visible timing regressions using synthetic audio and content-free trace identities

## 2. Provider Readiness

- [x] 2.1 Replace the global connection-open critical section with per-session-channel single-flight creation
- [x] 2.2 Return trackable prewarm futures and add a configurable bounded live-start readiness gate
- [x] 2.3 Add prewarm scheduled, ready, failed, timeout, and duration diagnostics with session cleanup

## 3. First Partial Delivery and Telemetry

- [x] 3.1 Ensure the first Desktop speech payload is emitted at the earliest valid attack/minimum-speech boundary without changing finalization
- [x] 3.2 Record only the earliest provider partial, transcript event, and browser paint for each utterance
- [x] 3.3 Add or update privacy-safe AI realtime evaluation cases for short Chinese, English, low-volume, and system-audio speech

## 4. Verification and Production

- [x] 4.1 Run focused Backend, Desktop, and Web regression tests
- [x] 4.2 Run full affected test suites, typechecks, production builds, and strict OpenSpec validation
- [ ] 4.3 Commit and push the tested revision, deploy compatible Backend/Web changes, and pass production health gates
- [ ] 4.4 Run a live recognizable-speech acceptance test on both channels and compare first-partial/final distributions without transcript content
