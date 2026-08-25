## Why

The macOS companion renderer repeatedly crashes during live interviews and leaves the surviving Electron window black. Native crash reports show the audio renderer creating hundreds of thousands of virtual-memory regions before Chromium terminates it with `SIGTRAP`, so the production companion is not stable enough for sustained dual-channel capture.

## What Changes

- Batch AudioWorklet samples into bounded 20–40 ms chunks before transferring them to the renderer instead of transferring every 128-sample render quantum.
- Throttle display-only audio health updates without delaying or coalescing audio frames sent to the realtime backend.
- Detect an unexpected Electron renderer exit and recreate the companion window so reopening the app cannot expose a permanently black surface.
- Add regression and soak-oriented tests for transfer cadence, cleanup, and renderer recovery.
- Publish a new signed and notarized macOS companion release for Apple Silicon and Intel without changing the bundle identifier or backend protocol.
- Instrument renderer/worklet/publisher resource trends without persisting raw audio or transcript content.
- Restore the active interview audio pipeline and publisher after an unexpected renderer exit, rather than only recreating the visible window.
- Replace boolean-only local capture reporting with evidence-backed STARTING/HEALTHY/DEGRADED/LOST/RECOVERING health and a one-second watchdog.
- Gate completion on real 60-minute system-only, microphone-only, and dual-channel soak tests.
- Add read-only, per-channel realtime transport amplification counters so abnormal outbound volume can be attributed without changing send, retry, ACK, queue, or reconnect behavior.
- Eliminate sequence-gap resend storms with a bounded in-flight window, ordered single-frame recovery, resume-offset reconciliation, unrecoverable-gap reset, and an amplification circuit breaker.
- Add backward-compatible Backend ingress protection so malformed or storming publishers cannot consume unbounded network and event-loop capacity.
- Require user-visible capture health to follow recent frame acknowledgements rather than a desired live-session state.
- Release the commercial transport correction as desktop patch version 1.1.1 and deploy the compatible Backend protection before publishing the new downloads.
- Keep non-critical browser performance acknowledgements bounded so telemetry cannot starve realtime audio acknowledgements.

## Capabilities

### New Capabilities
- `desktop-renderer-stability`: Covers bounded audio cross-thread transfer, sustained dual-channel capture, renderer crash recovery, and production release verification.

### Modified Capabilities

None.

## Impact

- Affects the Electron companion audio worklet, realtime publisher, main-window lifecycle, bounded Web performance telemetry, Backend realtime ingress safeguards, desktop/web/backend tests, package version 1.1.1, production deployment, and release artifacts.
- Preserves realtime protocol version `2.0` and existing frame/event shapes; it changes retry, recovery, admission protection, and health behavior without changing ASR, billing, RAG, screenshot persistence, or transcript semantics.
- Transport amplification diagnostics remain local to the companion process and do not add audio, counters, or identifiers to the backend protocol.
- Audio remains transient and is not newly persisted; batching changes only in-memory capture transport inside the desktop process.
