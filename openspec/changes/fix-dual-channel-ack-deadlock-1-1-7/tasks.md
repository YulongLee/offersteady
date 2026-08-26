## 1. Production Regression Coverage

- [x] 1.1 Add a transport regression for an unexpected remote code-1000 close and stale old-socket events after replacement
- [x] 1.2 Add reliability regressions proving continuous sends do not move the oldest pending deadline and a recovering channel cannot wait forever
- [x] 1.3 Add a publisher regression matching the production dual-channel failure where one replacement channel ACKs and the other fills its window
- [x] 1.4 Add an atomic resume regression for zero/non-zero offsets, retired-generation buffers, and contiguous next sequences

## 2. Deadlock-Free Runtime

- [x] 2.1 Make transport close intent and socket generation explicit and recover every unexpected active-socket close
- [x] 2.2 Track per-channel generation-local sent/ACK high-water marks, oldest pending age, and saturated-window progress
- [x] 2.3 Replace the global first-ACK recovery completion with channel-aware fresh-media acknowledgement state
- [x] 2.4 Allow watchdog evaluation during media recovery and trigger one bounded shared-transport replacement on stalled channel progress
- [x] 2.5 Reconcile sequencers, queues, in-flight markers, and send buffers atomically before resuming capture
- [x] 2.6 Extend metadata-only diagnostics with transport generation and per-channel progress without content or credentials

## 3. Verification and Soak

- [x] 3.1 Run focused Desktop transport, reliability, publisher, hot-switch, and renderer recovery tests
- [x] 3.2 Run Desktop typecheck, full test suite, production build, and Backend WebSocket compatibility tests
- [x] 3.3 Add and run a synthetic long-running dual-channel ACK-stall/recovery soak with bounded queues and no resend amplification
- [x] 3.4 Validate `fix-dual-channel-ack-deadlock-1-1-7` with strict OpenSpec validation and inspect the final diff

## 4. Companion 1.1.7 Release

- [x] 4.1 Increment companion and release metadata from 1.1.6 to 1.1.7 without changing bundle identifier or protocol 2.0
- [x] 4.2 Build and verify macOS arm64/x64 and Windows x64 1.1.7 artifacts with immutable checksums and required signing status
- [x] 4.3 Install and launch the verified local macOS 1.1.7 build using a recoverable 1.1.6 backup
- [ ] 4.4 Commit and push the tested revision, deploy any compatible server changes first, then publish the 1.1.7 companion manifest
- [ ] 4.5 Run metadata-only production health and live dual-channel acceptance checks, retaining 1.1.6 as rollback
