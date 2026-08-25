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

### Commercial transport storm remediation (2026-08-26)

- Live failure evidence: installed production companion 1.1.0 captured 27,112 system callbacks and 1,634 unique system frames, but made 1,253,984 WebSocket writes with zero ACKs in the observed session. Duplicate writes reached 1,252,350, reconnects reached 33, and the interval amplification ratio reached 511. This proves capture was active while delivery was trapped in a resend storm.
- Root cause: every `sequence-gap` response cleared the whole channel's sent set and replayed every queued frame. The client also ignored Backend `resumeOffsets`, flushed before receiving the authoritative cursor, and passed stale pending sequences into a newly-created publisher.
- Client remediation: each channel now permits at most eight unacknowledged writes; only the exact expected sequence is retried; repeated gap responses are suppressed for 500 ms; each sequence has a three-resend budget; missing recovery frames or an exhausted budget open the circuit and recreate both enabled capture sources with a fresh sequencer.
- Server remediation: eight consecutive sequence-gap events without progress return a retryable `sequence-gap-budget-exhausted` degraded event and close the connection with code 1013. Protocol version remains `2.0`.
- Health semantics: capture callbacks alone no longer move a source to `HEALTHY`; a fresh authoritative frame or terminal ACK is required after startup or recovery.
- Focused verification: 15 desktop transport/reliability tests passed; the Backend storm circuit-breaker regression passed.
- Full verification: 23 desktop test files / 101 tests passed; Backend 305 tests passed and 14 environment-dependent tests skipped; all-workspace TypeScript typecheck passed; all workspace production builds passed with the documented production Web environment; `git diff --check` passed; strict OpenSpec validation passed.
- Privacy: tests use synthetic metadata and synthetic bytes only. No interview audio or transcript content was persisted by this work.
- Deployment/publishing: none. The fix is implemented and locally verified, but production rollout and the real 60/60/60/120-minute soak gates remain separate release actions.

### Patch release 1.1.1 packaging (2026-08-26)

- macOS arm64 DMG: SHA-256 `40e8c71c500af493780941832c45153f037edc52258be4c14e0c8fd5399cf2a0`; App and DMG notarization Accepted; Developer ID, 16 Mach-O components, Gatekeeper and stapler passed.
- macOS x64 DMG: SHA-256 `1fa03520db74dec5a18dd1ad5b7653c549effef0a9130bf6788df28a23b2a86b`; App and DMG notarization Accepted; Developer ID, 16 Mach-O components, Gatekeeper and stapler passed.
- Windows x64 NSIS installer: SHA-256 `eab6185876447347b3ea184ec4f19a61b16be43e240482aba8aabc8535a899f6`; installer/executable structure passed; Authenticode remains unavailable and metadata remains non-verified.
- Bundle identifier remains `com.offersteady.companion`; realtime protocol remains `2.0`.
- Backend storm protection source commit `a9e99a4` was deployed first; production Backend, PostgreSQL and Redis passed health checks before the new desktop manifest was promoted.
- Verified artifacts were uploaded to `desktop-releases/<platform>/<architecture>/1.1.1/`; the checked-in production manifest is updated atomically in the follow-up publication commit.

### Patch release 1.1.1 production rollout (2026-08-26)

- Source commits `a9e99a4` and `fe53ba5` were pushed to `main`; production deploy metadata and the checked-out repository both resolve to `fe53ba5bc16fe62f20c38c1c953ebe3b3658349c`.
- Production Backend, PostgreSQL and Redis are healthy. The active Backend configuration enforces an eight-event sequence-gap budget without progress.
- The public desktop manifest reports version `1.1.1` for macOS arm64, macOS x64 and Windows x64 with the verified release checksums above.
- A public byte-range request for every download returned HTTP 206 with the expected object size: 126,798,359 bytes for macOS arm64, 130,341,085 bytes for macOS x64 and 102,142,838 bytes for Windows x64.
- A one-time synthetic production session connected through the public realtime WebSocket, received protocol `2.0` connection state, sent one 640-byte synthetic PCM frame and received authoritative `frame-accepted` ACK sequence `0`. The publisher and synthetic session were then closed and deleted.
- The notarized macOS arm64 1.1.1 app was installed locally after confirming capture diagnostics had been idle for more than one hour. Its version, strict code signature, Gatekeeper assessment and stapler ticket passed before launch; the prior 1.1.0 app remains as a recoverable backup.
- This controlled rollout verifies reachability and one-frame acknowledgement only. The real system-only, microphone-only, dual-channel and 120-minute soak gates remain pending and are not inferred from the synthetic probe.

### Production real-client hotfix verification (2026-08-26)

- The first 1.1.1 real interview reproduced a Backend `TypeError`: client diagnostics supplied `desktopWsSendAtMs` while `_prepare_audio_frame` also passed the same keyword explicitly. The WebSocket closed with 1011 before ACK, while the prior synthetic probe passed because it did not include real-client diagnostics.
- Regression coverage now sends negotiated binary audio with colliding diagnostic keys. Trace fields are merged once and authoritative Backend/session/frame timings override client diagnostics; the focused transport suite passed 11 tests and the full Backend suite passed 306 tests with 14 environment-dependent skips.
- After the trace fix, the real interview initially reached 516/516 SYSTEM ACKs, then exposed a second production issue: hundreds of concurrent browser `performance-ack` requests delayed the event loop beyond the three-second client ACK watchdog and caused publisher recreation.
- Web performance acknowledgements now use one in-flight request and at most sixteen pending measurements; excess diagnostic work is dropped. Backend acknowledgement processing runs outside the realtime event loop. A 64-event burst regression verified one maximum concurrent request and seventeen total processed requests (one active plus sixteen retained).
- Web verification passed 42 files / 287 tests and the documented production build. Backend verification passed 306 tests with 14 skips. Strict OpenSpec validation and `git diff --check` passed.
- Production commit and deploy marker both resolve to `3933bcf3fe6b8a952b4f3d147c83dc1d4c5d9112`; Backend and Web health checks passed.
- In the refreshed real interview, SYSTEM reached 1,264 acknowledged frames and MIC reached 128 acknowledged frames over more than three minutes of process uptime. Both channels had zero reconnects, resends and sequence gaps; send amplification remained 1.0 while audio was produced. Backend logs showed zero realtime WebSocket failures and exactly one publisher connection during the observed window.
- This live window verifies real dual-channel capture and sustained ACK recovery beyond both reproduced failure points. It does not replace the pending 60-minute system-only, microphone-only, dual-channel or 120-minute soak gates.

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
