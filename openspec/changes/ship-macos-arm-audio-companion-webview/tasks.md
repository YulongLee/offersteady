## 1. Protocol and Backend Contracts

- [x] 1.1 Extend protocol types for desktop architecture, local development artifact status, source health, source meters, and embedded workspace configuration.
- [x] 1.2 Define realtime speech WebSocket message schemas for device status, ordered audio frames, transcript revisions, source degradation, and acknowledgements.
- [x] 1.3 Add backend session-bound desktop device binding and credential validation needed by macOS companion publishing.
- [x] 1.4 Add backend realtime speech publish endpoint or WebSocket route for authorized desktop audio frames and status events.
- [x] 1.5 Add backend event fan-out so Web and embedded desktop workspace can load current device status and transcript state from the same session source.
- [x] 1.6 Add backend tests for valid binding, expired binding, unauthorized publish, ordered frames, duplicate frames, and source status sync.

## 2. Dual-Channel Role Routing and Speech Flow

- [x] 2.1 Implement source-based role routing so microphone/headset transcript events become “我” and system-audio events become “面试官”.
- [ ] 2.2 Implement source-degraded states for mixed, missing, disconnected, incompatible, silent, and permission-denied sources.
- [x] 2.3 Ensure automatic question triggering only consumes final system-audio interviewer questions.
- [ ] 2.4 Add echo/duplicate suppression across microphone and system audio before answer-task creation.
- [x] 2.5 Connect routed transcript events to the existing realtime conversation state used by the live workspace.
- [ ] 2.6 Add synthetic eval/test fixtures for microphone-only, system-audio question, candidate speech, echo, overlap, source loss, and reconnect.

## 3. macOS arm64 Desktop Audio Runtime

- [x] 3.1 Update desktop runtime capability detection to report macOS arm64, app version, protocol version, microphone permission, system-audio permission, and available sources.
- [x] 3.2 Implement microphone/headset enumeration, permission request, capture start/stop, and live level metering.
- [x] 3.3 Implement macOS system-audio permission check and capture path through Electron desktop capture or the selected macOS adapter.
- [x] 3.4 Keep microphone/headset and system-audio frames separate with stable source IDs, sequence numbers, timestamps, duration, codec, sample rate, and channel metadata.
- [ ] 3.5 Implement bounded in-memory frame buffering, acknowledgement tracking, reconnect resend, and explicit audio-gap reporting.
- [x] 3.6 Ensure stop, disconnect, app quit, and session end clear transient buffers and stop all active media tracks.
- [x] 3.7 Add desktop tests for capture state transitions, permission-denied states, silent-source diagnostics, frame sequencing, buffer limits, and no local recording writes.

## 4. Desktop UI and Embedded Web Workspace

- [x] 4.1 Add desktop UI sections for pairing/binding, source permissions, source meters, capture state, backend connection, and error recovery.
- [x] 4.2 Embed the OfferSteady Web workspace in the desktop shell with configurable default URL and an external-browser fallback.
- [x] 4.3 Keep capture controls visible outside or alongside the embedded Web workspace while the Web page is open.
- [x] 4.4 Ensure embedded Web runtime does not receive ASR keys, server API keys, device credentials, or raw audio buffers.
- [x] 4.5 Synchronize desktop capture state into the embedded workspace through backend state or a safe local bridge.
- [ ] 4.6 Add desktop renderer tests for the embedded workspace unavailable state, capturing indicator, permission guidance, and no hidden capture.

## 5. Web Download and Live Conversation Integration

- [x] 5.1 Add a local macOS Apple Silicon development artifact entry to the release/download manifest when a local desktop build exists.
- [x] 5.2 Update the Web device/download page to show the current development-machine artifact, architecture, version, capabilities, and local/development status.
- [x] 5.3 Show build instructions or unavailable state when the macOS arm64 artifact has not been generated.
- [x] 5.4 Update live conversation state loading so backend transcript events replace synthetic speaker fixture data in real sessions.
- [x] 5.5 Preserve the approved live workspace layout and keep only “面试官” and “我” in the conversation window.
- [ ] 5.6 Add Web tests for local artifact display, missing artifact guidance, dual-role transcript rendering, source degradation, and no role-correction UI.

## 6. Local Packaging and Developer Machine Verification

- [x] 6.1 Add or verify desktop build scripts for macOS arm64 development artifact generation.
- [x] 6.2 Generate a macOS arm64 local package or app directory on the current development machine.
- [x] 6.3 Record artifact metadata including version, architecture, file path, size, SHA-256 if available, protocol version, and development/local signing status.
- [x] 6.4 Verify the package can launch on the current Apple Silicon Mac and reports arm64 runtime.
- [x] 6.5 Document local run, local download, permissions reset, troubleshooting, and cleanup steps.

## 7. Privacy, Safety, and Observability

- [ ] 7.1 Redact raw audio bytes, full sensitive transcripts, binding tokens, device credentials, API keys, and provider payloads from logs.
- [x] 7.2 Add visible user-facing copy explaining microphone/headset as “我” and system audio as “面试官”.
- [x] 7.3 Verify the desktop companion cannot auto-start capture after app restart without explicit user action.
- [x] 7.4 Verify raw audio is not written to local files and server-side raw audio retention remains disabled by default.
- [ ] 7.5 Add structured monitoring for device online, source level, capture state, ASR state, reconnects, audio gaps, and degraded reasons.

## 8. End-to-End Verification

- [x] 8.1 Run backend tests covering desktop binding, realtime speech publishing, transcript routing, and state sync.
- [x] 8.2 Run protocol package tests covering audio, speaker, release, and compatibility contracts.
- [x] 8.3 Run desktop typecheck, desktop unit tests, and macOS arm64 package build.
- [x] 8.4 Run Web tests covering devices page, embedded-compatible live workspace, and dual-role conversation rendering.
- [ ] 8.5 Manually verify on the current Apple Silicon Mac: launch app, grant permissions, see both meters, start capture, see monitoring success, open embedded Web, and stop capture.
- [x] 8.6 Run `openspec validate ship-macos-arm-audio-companion-webview --strict`.

## Apply Notes

- Desktop build, typecheck, renderer tests, Web focused live tests, backend foundation tests, and OpenSpec strict validation passed on 2026-07-02.
- `npm run package:mac:arm64 -w @offersteady/desktop` now generates `apps/desktop/release/mac-arm64/面试稳伴随程序.app` and `apps/desktop/release/OfferSteady-Companion-0.1.0-macOS-arm64.zip`.
- The generated macOS arm64 app was verified with `open` after unsetting the Codex/terminal-only `ELECTRON_RUN_AS_NODE=1` environment variable.
- On 2026-07-02, the desktop app was updated with explicit Mac, microphone, system-audio, and screen-video diagnostic actions; the macOS arm64 local package was regenerated at `apps/desktop/release/OfferSteady-Companion-0.1.0-macOS-arm64.zip` with SHA-256 `9101910c8a4fce93b51b21da8759008b51c1f4c42062eaacfbdb79500485b1e2`.
- The diagnostics were tightened again on 2026-07-02 to prefer Electron's macOS system picker for display capture, show specific media failure reasons, and document `tccutil` permission reset steps. The regenerated macOS arm64 zip SHA-256 is `041cb64b206c4aaeafd5f80af75f4ec959c89d641bfba5381b9ab496c8e988d5`.
- The desktop companion UI was simplified on 2026-07-02 with a single "一键授权并检测" action, primary audio waveforms, and a screen preview panel above device details. The regenerated macOS arm64 zip SHA-256 is `bf77cc914ab02c13d10474fbbf9d4796eedd35c1502307add9a3bbd6c6648357`.
- The desktop companion UI was corrected again on 2026-07-02 to match the requested terminal-style reference: only microphone selection, system-audio selection, screen selection/preview, connection code/status, and homepage/tutorial links remain visible. The window was widened for the four-row layout, display sources are listed through a safe desktop IPC, the connection-status web link opens the local workspace, and the regenerated macOS arm64 zip SHA-256 is `1063453208e0e873f673ec688082a6a4aba9062dfdd13eab10e12107c339effd`.
- The device rows were adjusted on 2026-07-02 without changing the requested terminal-style row structure: the "麦克风", "系统音频", and "系统截屏" sections remain in place, while source availability is shown through red/green indicator lights for "我的声音", "面试官声音", and "截屏屏幕". Device selection does not trigger separate authorization/test actions. The regenerated macOS arm64 zip SHA-256 is `9cb6b4dfc332d9f514aae13201fec37f4562ab16d634e08394f0d2751d27ed1e`.
- The desktop companion visual style was aligned with the Web product design on 2026-07-02: it now uses the Web palette (`#080c13`, `#101721`, `#6ee7bd`), translucent panels, thin borders, brand-green status treatment, and Web-like button/code styles while preserving the approved companion row structure and behavior. The regenerated macOS arm64 zip SHA-256 is `fad35f350bfd1fa38b6100f66e503314967021c92f01e7bc84491e4b9e6694e1`.
- The companion window was compacted on 2026-07-02 so the full assistant fits within a small desktop panel: default window size is now `720x560`, minimum size is `620x500`, and row heights, header, controls, connection card, and footer spacing were reduced while preserving the existing section structure. The regenerated macOS arm64 zip SHA-256 is `db459d2b67a60afb08b6f7554c14ac6afd189e6074404ece622baccc97f4360c`.
- The desktop/web binding loop was tightened on 2026-07-02: the desktop app now uses "屏幕捕捉" wording, polls the backend for a machine-code binding after registration, switches to connected/capturing state when the Web preparation page binds the code, and publishes device status to the bound interview session. The Web live page now reads realtime device-status events alongside transcripts so the visible capture state reflects the desktop companion. The regenerated macOS arm64 zip SHA-256 is `429b9fb22f2c1ee8263d343777a175a2ba34bb51ea43de2d4e54406a91bca837`.
- On 2026-07-02, the desktop audio runtime was connected to the backend Realtime Speech pipeline: the companion now opens one publisher for the selected microphone and one for system audio, converts both streams to 16k PCM frames, segments speech locally, and pushes real audio frames to `/api/v1/realtime-speech/ws`. The backend now accepts device/source PCM metadata and uses the configured DashScope realtime ASR gateway when `OFFERSTEADY_REALTIME_ASR_API_KEY` is present, while tests continue to fall back to the synthetic gateway. A smoke roundtrip against the configured realtime model returned a transcript from real PCM input.
- On 2026-07-02, the desktop companion regained pre-bind local audio diagnostics: before the webpage is bound, the selected microphone and system-audio sources now start a local monitor, show inline volume bars next to each selector, and surface silent/permission-denied/unavailable states so headset and system-audio capture can be verified before entering an interview. The regenerated macOS arm64 zip SHA-256 is `a4a9131c0ae278ff6653e5914cd8110def4483641d4cbd12ec032c7152fd0518`.
- On 2026-07-02, the companion status semantics were tightened for real interview diagnostics: microphone/system-audio lights now turn green only when live signal is detected, system audio silent state explicitly says the meeting audio channel is connected but no conference voice is detected, the meter scale was made more sensitive for app audio such as WeChat calls, the screen row no longer shows shortcut settings, and the screen preview area remains visible with either the selected display thumbnail, live preview, or an explicit empty state. The regenerated macOS arm64 zip SHA-256 is `01ca713ebc7ca875a9942c1847718bd4150ceda878ab62f2d25586070bcc1d8c`.
- On 2026-07-02, the system-audio product model was corrected from display-bound capture to computer output loopback: the companion now labels the source as "电脑输出音频", requests audio-only display media for output loopback, handles audio-only requests in the Electron display media handler without selecting a screen, and leaves screen capture as a separate screenshot/preview capability. The regenerated macOS arm64 zip SHA-256 is `a5123b1549054304aca0add52a00fab10399e3f7bfce0718b22480abf3bbb598`.
- On 2026-07-02, the desktop/web realtime loop was tightened for the current联调: after the Web page binds a machine code, the companion now treats the active backend binding as the connected state, consumes backend WebSocket transcript/degraded events, and shows "已连接 | 网页端已绑定本机" while audio frames continue publishing. The backend realtime WebSocket now reports per-frame ASR degraded events without closing the stream, so a failed ASR segment does not block later transcript updates. Backend tests are isolated from local runtime machine-code state, protocol contract tests were updated to current `authentication` and `realtime-speech` feature areas, and the regenerated macOS arm64 zip SHA-256 is `2fa8908d7854eaf277dec2249f1254b45197bde089f5ce36009752b735280f9b`.
- On 2026-07-02, the machine-code binding diagnostics were tightened after local联调 feedback: the desktop renderer now treats non-2xx device registration as a real failure instead of silently showing a waiting state, displays the backend API URL and last registration/binding-query result in connection management, and the backend active-binding lookup now falls back to the latest binding by machine code when a local device id changes or drifts. The regenerated macOS arm64 zip SHA-256 is `082a10711e6d76ca24695b94bf59bbbb47f3afbf1197dc89bcf283681d9c5411`.
- On 2026-07-02, the binding sync path was changed to machine-code-first after further local联调 feedback: the backend now exposes `/api/v1/realtime-speech/desktop-devices/by-code/{manualCode}/binding`, and the desktop companion polls that endpoint every second before falling back to the device-id endpoint. This matches the product model that the 6-digit machine code is the user-visible pairing key, so after the Web page verifies the code the companion should switch to connected without depending on a stable local device id. The regenerated macOS arm64 zip SHA-256 is `4bf946a3f05105be39bb7fdae2af7d502c60334c5febb28aea0fb8b088fb0a85`.
- On 2026-07-02, the binding sync was hardened again with a backend pairing status endpoint: `/api/v1/realtime-speech/desktop-devices/pairing-status?manualCode=...&deviceId=...` now returns `not-registered`, `registered`, or `bound` in a 200 response, and the desktop companion uses that as the primary connection source of truth. Local curl verification returned `state=bound` for the active development machine code before packaging. The regenerated macOS arm64 zip SHA-256 is `b75fb8a774305f9e8fb05c576a908d6443de707dd16229b11ff242039773e8c2`.
- On 2026-07-02, the desktop connection state machine was split between pairing and live capture: the backend pairing-status response now includes the bound interview `sessionStatus`, the companion displays "已连接" as soon as the Web page binds the machine code, and it waits until `sessionStatus=live` before creating realtime audio publishers. This prevents preparation-page binding from being overwritten by publisher creation failures while the session is still `preparing`. A local API simulation verified `registered -> bound/preparing -> bound/live`. The regenerated macOS arm64 zip SHA-256 is `f775e6e54ad46f2bb32a665a5442ccae3e1a24d7f8e0c385156306f4972948f7`.
- On 2026-07-02, the packaged companion backend networking was moved out of the `file://` renderer into an Electron main-process API proxy after local screenshots showed `Failed to fetch` from the renderer while Web/backend binding succeeded. Device registration, pairing-status polling, device-status publishing, and realtime publisher token creation now use `window.offersteady.apiRequest(...)` backed by `ipcMain` + Node `fetch`, avoiding renderer CORS/security-policy failures against `http://127.0.0.1:8000/api/v1`. The regenerated macOS arm64 zip SHA-256 is `1842749fb39834694184c133b72b9351a4e8ed97d5705fa0fa0af028dafe9580`.
- On 2026-07-02, the live audio capture runtime was hardened after local联调 showed both microphone and computer-output meters staying idle during a connected live interview. The realtime publisher now starts microphone and computer output independently, reports local source health even when the WebSocket is not yet open, keeps the audio graph alive through a zero-gain sink, lowers the speech detection threshold for AirPods/low-level output, and no longer lets one failed source stop the other. The companion connection info now shows the latest diagnostic instead of hiding failures behind a generic "正在同步" message. The regenerated macOS arm64 zip SHA-256 is `68788c3d7a69bb69afa38a10d1ef6a933f728c3b27bc26edb46079341ff6bb8f`.
- The previous `electron-builder` path is retained as `package:mac:builder:arm64`; it stalled inside `electron-builder` after `packaging platform=darwin arch=arm64 ... appOutDir=release/mac-arm64`.
