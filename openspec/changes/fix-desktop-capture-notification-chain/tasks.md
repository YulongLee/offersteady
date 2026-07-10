## 1. Runtime Diagnostics and Evidence

- [x] 1.1 Add or update desktop runtime diagnostics to report local microphone signal, computer-output signal, produced frame count, backend receipt count, ASR status, transcript count, screen preview status, and screenshot upload status without storing raw media.
- [x] 1.2 Ensure backend realtime runtime exposes current-session frame receipts, failed ASR states, transcript counts, source ids, and provider error codes needed by desktop/web diagnostics.
- [x] 1.3 Add a synthetic non-sensitive PCM probe path or script that verifies backend frame ingestion, ASR completion/failure surfacing, and transcript availability.

## 2. Computer Output Capture

- [x] 2.1 Audit the current macOS `SystemAudioAdapter` and Electron desktop capture path to determine why local video playback does not move the computer-output meter.
- [x] 2.2 Fix the system-output capture adapter or add a macOS fallback adapter boundary so local playback creates real local signal updates when supported.
- [x] 2.3 Ensure the companion marks computer output as waiting/unsupported/error when no real signal or backend frame receipts exist.
- [ ] 2.4 Verify computer-output frames are published to backend for the bound live session and reflected in runtime receipts.

## 3. Screen Capture and Screenshot Requests

- [x] 3.1 Audit desktop screen listing, preview, native runtime health, permission handling, and selected-screen propagation.
- [x] 3.2 Fix screen preview so selecting a display and clicking preview shows a real preview or a specific permission/runtime error.
- [x] 3.3 Fix screenshot-answer capture handling so web requests either upload a real selected-screen capture or mark the request failed with a user-readable reason.
- [ ] 3.4 Verify screen capture behavior in the packaged macOS app, not only the dev renderer.

## 4. Interview Entry Notification and Stable Connection Copy

- [x] 4.1 Centralize desktop connection copy so unbound state stays stable and does not flicker during polling.
- [x] 4.2 Add a visible desktop notification/status transition when a web interview binds the machine code.
- [x] 4.3 Add a visible desktop notification/status transition when the bound interview enters live capture and audio publishing starts.
- [x] 4.4 Ensure user-facing connection copy does not expose backend API URLs and provides a clickable interview-home action.

## 5. Full-chain Self-test and Packaging

- [x] 5.1 Run the desktop/backend realtime diagnostic against a current live session and record stage-by-stage results.
- [ ] 5.2 Manually test local video playback, computer-output meter movement, frame receipts, and web live-conversation display.
- [ ] 5.3 Manually test screen preview and screenshot-answer request from web to desktop and back to backend.
- [x] 5.4 Rebuild the macOS local release package and confirm the packaged app contains the fixes.
- [x] 5.5 Update docs with the final troubleshooting runbook, known macOS limitations, and self-test commands.
- [x] 5.6 Run `openspec validate fix-desktop-capture-notification-chain --strict` and resolve any spec/task issues.
