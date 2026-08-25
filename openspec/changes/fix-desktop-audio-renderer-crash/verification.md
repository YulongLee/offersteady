## Verification Summary

- Desktop tests: 22 files, 93 tests passed.
- Desktop TypeScript typecheck: passed.
- Desktop production build: passed.
- Synthetic dual-channel soak: 30 interview minutes at 48 kHz; 168,750 bounded transfers versus 1,350,000 legacy transfers (87.5% reduction), with a 21.33 ms transfer interval.
- OpenSpec strict validation: passed.

## Desktop Realtime Audio Reliability P0

- AudioWorklet aggregation: verified at 1,024 samples per renderer message (about 21.33 ms at 48 kHz), rather than one allocation/message per 128-sample callback.
- Resource instrumentation: worklet callback/message rates, audio throughput, controlled typed-array/ArrayBuffer ownership, renderer RSS/private memory, JS heap, active tracks/nodes/contexts/listeners/timers and React render rate are wired into bounded heartbeat samples.
- Reliability state: `STARTING`, `HEALTHY`, `DEGRADED`, `LOST` and `RECOVERING` are derived from real capture, produced-frame, sent-frame, ACK and provider-append timestamps.
- Watchdog: one-second checks cover capture stalls over two seconds and pending ACK stalls over three seconds, with bounded source or transport recovery.
- Forced renderer termination: main process observed `render-process-gone` (`reason=killed`, `exitCode=9`) and created a new renderer process. This verifies process recreation only.
- Live publisher restoration after renderer loss: not yet accepted. The available production pairing was bound to an ended interview, so no live System/Mic frame or fresh frame ACK could be produced after recovery.
- Real soaks: system-only 60 minutes, microphone-only 60 minutes, dual-channel 60 minutes and follow-up 120 minutes remain pending. No simulated result is substituted for these tests.
- Deployment/publishing: none performed for the P0 reliability work.

### Real environment fail-fast observation (2026-08-25)

- Environment: notarized production 0.1.20 app, real live interview binding, real macOS system-audio playback and production backend.
- Permission precondition: the first attempt was invalid because the local ScreenCapture permission was denied. After the user enabled Screen & System Audio Recording and restarted the app, the binding returned to `live` / `capturing`.
- Observation window: about 20 minutes. The renderer PID remained stable and no renderer crash or unexpected restart was observed in this window.
- Renderer RSS: approximately 121–140 MiB during observed samples; no monotonic linear growth was established in this short window.
- Renderer CPU: approximately 10–18% while the real audio session was active.
- Electron network-service CPU: approximately 11–12%.
- Electron network-service outbound bytes: about 4.95 GB by 20 minutes. A five-second sample increased by about 13.6 MB, with instantaneous one-second deltas ranging from about 1.2 MB to 4.6 MB.
- The dominant connection was the app network service's production proxy socket; the second socket was materially smaller. This is consistent with one real-time channel producing excessive transport volume, but source attribution requires server event/ACK evidence and is not inferred from socket totals alone.
- Verdict: fail fast. The real 60-minute soak was not continued because the observed transport amplification and sustained CPU load already violate the reliability objective and would waste network/server resources.
- No renderer was killed, no live recovery was forced, and no application/server code was changed during this observation.

### Read-only transport amplification instrumentation (2026-08-25)

- Scope: local companion observation only; no send, retry, ACK, sequence-gap, queue, reconnect, backend protocol or server behavior was changed.
- Per-channel counters: AudioWorklet capture frames, publisher input frames, unique `channel+seq` writes, actual WebSocket sends, exact audio/total envelope bytes, ACKs, last sent/acked sequence, resends, gap recovery, reconnects, ring/retransmit depths, listener concurrency and unexpected non-PCM16 formats.
- Amplification: ten-second interval ratios compare actual sends/bytes with distinct sequences and their expected audio bytes in the same interval. Ratios over 1.2 are abnormal, over 2 severe, and 10 or more a resend storm.
- Duplicate evidence: bounded tracking keeps at most 8,192 recent sequences per channel and reports the top 20 repeated sequences; no PCM or transcript content is retained.
- Local evidence path: Electron main writes rotating NDJSON to the app user-data directory as `realtime-audio-transport-diagnostics.ndjson` (5 MiB current file plus one previous file).
- Verification: 23 desktop test files / 97 tests passed; desktop TypeScript typecheck passed; production build passed; `git diff --check` passed; strict OpenSpec validation passed.
- Deployment/publishing: none. The currently running notarized 0.1.20 app does not contain these new counters, so the prior 4.95 GB sample cannot be retroactively attributed to audio payload until a controlled diagnostic build is run.

## macOS arm64

- Version: 0.1.20
- Bundle identifier: `com.offersteady.companion`
- Notarization: Accepted (`f2753d56-9379-4c87-8918-761274037836`)
- Strict code-sign verification: passed, including 16 Mach-O components.
- Gatekeeper app and DMG assessment: accepted, Notarized Developer ID.
- Stapler validation: passed.
- DMG: `apps/desktop/release/macos-production/OfferSteady-Companion-0.1.20-macOS-arm64.dmg`
- SHA-256: `5fe771a205e4942eaef53ccf789affeb12f469e9ab1bace342489a723bf83458`

## macOS x64

- Version: 0.1.20
- Bundle identifier: `com.offersteady.companion`
- Notarization: Accepted (`121c1e3d-32a6-4c6d-900a-510ff194ccce`)
- Strict code-sign verification: passed, including 16 Mach-O components.
- Gatekeeper app and DMG assessment: accepted, Notarized Developer ID.
- Stapler validation: passed.
- DMG: `apps/desktop/release/macos-production/OfferSteady-Companion-0.1.20-macOS-x64.dmg`
- SHA-256: `7056e36c6dd89747894c6775d6b1abe524ea7800d13fb05de7ac554c9e58a361`

The verified artifacts are ready for controlled distribution but were not uploaded to the website or deployed by this change.
