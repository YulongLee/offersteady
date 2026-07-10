## Why

The current desktop companion breaks the core live interview journey: computer output shows no meter movement during local playback, screen capture does not work, and entering an interview gives no clear notification or diagnostic feedback. These are blocking prototype issues because users cannot trust whether the assistant is connected, listening, capturing, or failing.

## What Changes

- Add a reliable desktop capture contract for macOS-first MVP behavior across microphone, computer output, screen capture, interview binding, and runtime diagnostics.
- Make computer output capture prove itself with real signal level, produced frames, backend receipts, and clear unsupported/error states when capture is unavailable.
- Make screen capture prove itself with a real preview/capture result and a clear permission/runtime failure message when capture is unavailable.
- Add a user-visible notification/status transition when an interview session binds this desktop companion and when the session enters live capture.
- Add a repeatable full-chain diagnostic and self-test path covering local signal detection, frame publishing, backend runtime receipts, ASR transcript flow, and screenshot upload/capture flow.
- Keep privacy boundaries: diagnostics may include state, timing, counters, and error codes, but must not persist raw audio, screenshots, interview transcripts, or personal files unless the existing product flow explicitly does so.

## Capabilities

### New Capabilities

- `desktop-capture-reliability`: Defines observable behavior for desktop companion audio capture, screen capture, interview-entry notifications, and full-chain diagnostics.

### Modified Capabilities

- None.

## Impact

- Desktop companion renderer and main process capture adapters under `apps/desktop`.
- Backend realtime speech runtime, device status, frame receipt, and transcript APIs under `apps/backend`.
- Screenshot answer desktop capture request flow under `apps/backend` and `apps/web`.
- Protocol types in `packages/protocol` if additional diagnostic fields are needed.
- Local release packaging and troubleshooting documentation in `docs/desktop-distribution.md` and related integration docs.
