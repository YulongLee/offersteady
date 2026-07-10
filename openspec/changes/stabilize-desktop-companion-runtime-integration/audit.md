## Desktop Companion Runtime Audit

Date: 2026-07-02

## 1. Desktop launch, machine code and backend URL path

- Desktop runtime config is created in `apps/desktop/src/main/index.ts`.
- Default Web URL: `http://localhost:5173/app`.
- Default API URL: `http://127.0.0.1:8000/api/v1`.
- The desktop app registers its persisted `deviceId/manualCode` to `POST /api/v1/realtime-speech/desktop-devices/register` in the Electron main process and again from the renderer.
- Risk: Web and desktop can point to different hosts/origins even on the same machine. If Web uses another `VITE_API_BASE_URL`, backend registration and Web binding will not meet.

## 2. Web preparation binding and live start path

- Web binds a machine code through `POST /api/v1/realtime-speech/sessions/{sessionId}/desktop-binding`.
- Backend stores the latest binding by machine code.
- Web starts the interview through the session start API.
- Desktop currently polls pairing status, but pairing status is too thin: it reports bound/live, but not publisher, media, frame, ASR or transcript progress.

## 3. Media source path

- Microphone uses `navigator.mediaDevices.getUserMedia({ audio: { deviceId }, video: false })`.
- System output currently uses `navigator.mediaDevices.getDisplayMedia({ audio: true, video: false })` with Electron `audio: "loopback"`.
- Risk: macOS/Electron may not produce real computer-output audio from audio-only display media. A static “电脑输出音频” option can appear selectable while no real loopback frames are produced.
- Screen list uses Electron `desktopCapturer.getSources` thumbnails.
- Screen preview currently prefers the thumbnail if available, which does not prove real screen capture permission or a live preview stream.

## 4. Realtime publisher path

- Desktop creates source-specific publishers through `POST /api/v1/realtime-speech/publishers`.
- Desktop opens WebSocket `/api/v1/realtime-speech/ws?token=...`.
- Desktop sends audio frames only when local RMS crosses the speech segmenter threshold.
- Backend transcribes each received frame and stores transcript segments.
- Risk: backend runtime only returns publisher count/state and transcript count; it does not expose frame receipts, ASR failures or per-source health to the companion.

## 5. Failure matrix

| Observed issue | Likely broken stage | Required correction |
| --- | --- | --- |
| Web binds code but companion remains “未连接” | Backend runtime state is not a single source of truth for companion | Add stage-based runtime status and consume it from desktop |
| Microphone selected but no movement | Permission/device/AudioContext/track/signal not separately reported | Add staged source health and signal/frame counters |
| Computer plays WeChat audio but system meter does not move | Electron loopback path unsupported or not producing signal | Add real signal detection and explicit `adapter-required/unsupported` state |
| Screen preview not visible | Thumbnail preview is not a live capture proof | Make preview open a real display stream and mark ready only after capture opens |
| Realtime conversation empty | Frames/ASR/transcripts not visible as one chain | Add backend frame receipts and runtime diagnostics; Web consumes backend transcript list |
