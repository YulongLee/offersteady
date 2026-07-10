## 1. Root Cause Confirmation

- [ ] 1.1 Capture a diagnostic report from the current failed companion showing microphone, computer output and screen stages.
- [ ] 1.2 Verify whether current Electron media capture can produce microphone frames on the user's Mac; if not, record the exact permission/device error.
- [ ] 1.3 Verify whether current Electron media capture can produce computer-output frames from WeChat or browser playback; record whether this path is unsupported.
- [ ] 1.4 Verify whether current Electron screen preview can produce a live frame; record the exact failure.
- [x] 1.5 Confirm the stale binding path that returns `session-6b94aa...` without an active Web page heartbeat.

## 2. Native macOS Capture Runtime

- [x] 2.1 Add a macOS capture runtime boundary for microphone, computer output and screen frame events.
- [ ] 2.2 Implement microphone capture using macOS native APIs and emit level/PCM frame events.
- [ ] 2.3 Implement computer-output capture using ScreenCaptureKit or an approved native path and emit level/PCM frame events.
- [ ] 2.4 Implement selected-display screen preview frame capture using the same runtime boundary.
- [x] 2.5 Add runtime process health checks and packaging validation so a package missing the native helper is marked invalid.

## 3. Fresh Binding and Heartbeats

- [x] 3.1 Add Web session heartbeat API for preparation and live pages.
- [x] 3.2 Add desktop device heartbeat generation and TTL.
- [x] 3.3 Change backend pairing status to return active binding only when Web heartbeat, desktop heartbeat, generation and session state are valid.
- [x] 3.4 Mark old latest bindings stale and prevent them from showing as connected in the companion.
- [x] 3.5 Add backend tests for closed Web page, closed desktop companion, ended session and same-code new generation.

## 4. Capture Validation Gate

- [ ] 4.1 Add companion self-check that requires microphone signal/frame, computer-output signal/frame and screen preview frame before ready state.
- [x] 4.2 Add actionable error codes for permission missing, unsupported macOS, native runtime missing, no signal and no frame.
- [x] 4.3 Ensure the UI never shows “已连接/正在收音/捕捉屏幕” unless validation and fresh binding are both true.
- [x] 4.4 Preserve the current companion visual style while changing only state and behavior.

## 5. Realtime Bridge Verification

- [ ] 5.1 Publish native microphone frames to backend Realtime Speech and verify Web displays “我”.
- [ ] 5.2 Publish native computer-output frames to backend Realtime Speech and verify Web displays “面试官”.
- [ ] 5.3 Verify quick answer uses the latest current-session interviewer transcript, not stale transcripts.
- [ ] 5.4 Add diagnostics that separate native capture, transport, ASR and Web consumption failures.

## 6. Packaging and User-Machine Validation

- [ ] 6.1 Package macOS arm64 companion with the native capture runtime included.
- [ ] 6.2 On the user's Mac, validate microphone wave movement by speaking.
- [ ] 6.3 On the user's Mac, validate computer-output wave movement by playing WeChat/browser/meeting audio.
- [ ] 6.4 On the user's Mac, validate selected-display preview frame.
- [ ] 6.5 On the user's Mac, bind from Web, start interview, and verify realtime transcripts appear on the Web page.
- [ ] 6.6 Update desktop distribution docs with minimum macOS version, permissions and known fallback path.
