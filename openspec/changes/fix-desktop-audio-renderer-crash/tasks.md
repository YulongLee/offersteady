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
