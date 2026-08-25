## 1. Audio Capture Stability

- [x] 1.1 Batch AudioWorklet input into 1,024-sample transferable buffers
- [x] 1.2 Bound renderer-facing health and meter update cadence without throttling audio transport
- [x] 1.3 Add deterministic regression tests for worklet batching and health throttling

## 2. Renderer Recovery

- [x] 2.1 Add bounded `render-process-gone` BrowserWindow recreation in the Electron main process
- [x] 2.2 Add regression coverage for recovery policy and clean shutdown behavior

## 3. Verification and Release

- [x] 3.1 Run desktop tests, typecheck, production build, and synthetic sustained dual-channel soak
- [x] 3.2 Bump desktop version and release metadata to 0.1.20 without changing the bundle identifier
- [x] 3.3 Build, sign, notarize, staple, and verify the arm64 macOS DMG
- [x] 3.4 Build, sign, notarize, staple, and verify the x64 macOS DMG
- [x] 3.5 Validate the OpenSpec change and record final artifact paths and verification results

## 4. Desktop Realtime Audio Reliability P0

- [x] 4.1 Add bounded worklet/publisher/renderer/React resource counters and trend snapshots
- [x] 4.2 Add deterministic leak/cadence regression coverage for callbacks, listeners, timers, tracks, nodes and contexts
- [x] 4.3 Persist session-safe renderer recovery metadata in main and restore the live binding after `render-process-gone`
- [ ] 4.4 Recreate capture sources, AudioWorklet, publisher and WebSocket after renderer recovery; verify recovery with a fresh frame ACK
- [x] 4.5 Add the STARTING/HEALTHY/DEGRADED/LOST/RECOVERING local reliability state machine
- [x] 4.6 Add the one-second capture/transport watchdog with bounded source and publisher recovery
- [x] 4.7 Add regression tests for zombie capture prevention and recovery from callback/ACK stalls
- [x] 4.8 Run desktop unit tests, typecheck and production build
- [ ] 4.9 Run and record real 60-minute system-only soak
- [ ] 4.10 Run and record real 60-minute microphone-only soak
- [ ] 4.11 Run and record real 60-minute dual-channel soak
- [ ] 4.12 If all 60-minute soaks pass, run and record the 120-minute soak
- [x] 4.13 Validate the OpenSpec change and update verification evidence without deploying or publishing

## 5. Realtime Transport Amplification Diagnosis

- [x] 5.1 Add bounded per-channel capture, publisher, unique sequence, WebSocket byte, ACK, resend, gap, reconnect, queue, listener and duplicate-sequence counters
- [x] 5.2 Emit local ten-second SYSTEM/MIC summaries and bounded duplicate-sequence samples without changing transport behavior
- [x] 5.3 Add deterministic regression coverage for normal 1x sends, duplicate sends, gap recovery, reconnect and amplification thresholds
- [x] 5.4 Run desktop tests, typecheck, build and strict OpenSpec validation; do not deploy or publish

## 6. Commercial Transport Storm Remediation

- [x] 6.1 Implement a bounded per-channel in-flight window and advance it only from authoritative ACKs
- [x] 6.2 Reconcile connection resume offsets, resend only the requested sequence, and reset the publisher when the expected frame is unavailable
- [x] 6.3 Add duplicate-gap suppression, resend budgets, an amplification circuit breaker, and Backend storm protection without changing protocol version 2.0
- [x] 6.4 Ensure ACK-stalled or reset transports stop reporting healthy capture and restart both enabled sources with fresh sequencing after renderer or publisher recovery
- [x] 6.5 Add deterministic desktop/backend regressions for queued gaps, missing expected frames, repeated gaps, resume offsets, ACK stalls and storm bounds
- [x] 6.6 Run focused and full tests, type checks, production builds and strict OpenSpec validation; record verification without deploying or publishing

## 7. Patch Release 1.1.1

- [x] 7.1 Bump the shared companion patch version from 1.1.0 to 1.1.1 without changing the bundle identifier or protocol version
- [x] 7.2 Build and verify production companion artifacts for macOS arm64, macOS x64 and Windows x64
- [x] 7.3 Commit and push the verified release source, then deploy the compatible Backend protection to production
- [x] 7.4 Publish the 1.1.1 desktop artifacts and atomically update the production download manifest
- [x] 7.5 Verify public health, build metadata, download metadata/checksums and one controlled live frame ACK after rollout

## 8. Production Trace Collision Hotfix

- [x] 8.1 Reproduce real-client diagnostic keys colliding with authoritative Backend trace fields
- [x] 8.2 Merge trace diagnostics without duplicate keyword arguments and preserve authoritative frame timings
- [x] 8.3 Reproduce a browser performance-ack burst and verify that request concurrency is bounded
- [x] 8.4 Serialize and bound Web performance acknowledgements, and offload Backend acknowledgement processing from the realtime event loop
- [x] 8.5 Run Web/Backend regression and build verification, deploy the hotfix and verify sustained ACK progress from the active real interview
