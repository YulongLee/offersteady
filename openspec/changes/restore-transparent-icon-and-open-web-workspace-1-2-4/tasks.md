## 1. Icon Regression Repair

- [x] 1.1 Restore approved 1024 px packaging and 256 px renderer icon assets with real alpha channels, transparent external corners, no text, and the shield/microphone/check mark
- [x] 1.2 Replace opaque-hash regressions with semantic tests for dimensions, alpha-capable color type, transparent corner pixels, shared brand family, and macOS/Windows packaging references
- [ ] 1.3 Regenerate and inspect macOS `.icns` and Windows `.ico` resources at small launcher sizes

## 2. Website Workspace Navigation

- [x] 2.1 Change the connection-card action to use the normalized configured `/app` workspace and remove active-session live-route construction from that action
- [x] 2.2 Replace the bound-state “进入当前面试” copy with stable website/workspace wording while preserving the binding status indicator
- [x] 2.3 Add bound, unbound, production-origin, local-fallback, and no-state-mutation regression tests for the website action

## 3. Version and Product Regression

- [x] 3.1 Increment desktop package and release metadata to 1.2.4 for macOS arm64, macOS x64, and Windows x64
- [x] 3.2 Verify the 1.2.3 layout, capture controls, permissions, device identity, binding lifecycle, realtime transport, screenshot workflow, homepage action, guide action, bundle identifier, protocol, and production origins remain unchanged
- [x] 3.3 Run desktop tests, typecheck, main/renderer production builds, OpenSpec strict validation, and privacy/product-boundary checks
- [x] 3.4 Restore fixed microphone/computer-output row copy, remove the conditional inline permission button, and add a layout regression

## 4. Live Start, Endpointing, and Health Recovery

- [x] 4.1 Shorten the registered/waiting companion binding cadence and make ASR prewarm non-blocking for the user-facing start response
- [x] 4.2 Bound commercial system-audio turns below the 1.2.3 twelve-second limit while preserving incremental revision continuity
- [x] 4.3 Add last-meaningful-speech-to-publish telemetry and regression coverage for silence and forced-boundary completion
- [x] 4.4 Clear stale transport error/reconnect fields on healthy source and ACK recovery, with regression coverage
- [x] 4.5 Refresh runtime health after device-status changes and implement a real authoritative Web re-diagnosis action
- [x] 4.6 Add regressions for recovered banners, non-optimistic diagnosis, live-start timing, and no changes to billing/privacy behavior

## 5. Cross-Platform Release

- [ ] 5.1 Build macOS arm64 and macOS x64 artifacts and verify native architectures, Developer ID identity, Hardened Runtime, notarization, stapling, Gatekeeper acceptance, icon resources, and SHA-256 values
- [ ] 5.2 Build the Windows x64 installer and verify executable architecture, truthful signing state, icon resources, installer behavior, and SHA-256 value
- [ ] 5.3 Perform clean-install visual checks for the downloaded file, installed application, Dock/launcher/taskbar, and in-app icon on representative supported systems
- [ ] 5.4 Publish synchronized 1.2.4 release metadata and artifacts only after all gates pass, retain 1.2.3 rollback files, and verify public redirects/range downloads
- [ ] 5.5 Record the release report with exact artifact names, sizes, checksums, signing/notarization results, icon verification, navigation verification, and any physical-platform limitations
