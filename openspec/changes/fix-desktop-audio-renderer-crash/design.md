## Context

The companion is Electron 42 (Chromium 148) and captures microphone plus system audio in the renderer. Each AudioWorklet render quantum currently allocates a new `Float32Array` and transfers its backing buffer to the renderer. At 48 kHz that is about 375 transfers per second per channel. Five macOS crash reports from versions 0.1.17–0.1.19 show the renderer terminating with the same `EXC_BREAKPOINT/SIGTRAP` signature after accumulating roughly 130,000–266,000 virtual-memory regions. The Electron main process survives, and because it only calls `show()` on the existing window, users see a black window afterward.

## Goals / Non-Goals

**Goals:**

- Keep cross-thread audio transfer bounded while preserving low-latency realtime audio frames.
- Prevent display-only health rendering from running at audio callback frequency.
- Recover the Electron UI automatically after an unexpected renderer exit.
- Produce signed and notarized 0.1.20 DMGs for arm64 and x64.
- Prove that renderer memory, ArrayBuffer use, CPU, worklet traffic, timers, listeners, media tracks, audio nodes and React updates remain bounded during sustained capture.
- Recover the current live interview capture and publisher after renderer recreation and verify recovery with fresh frame production and acknowledgement.
- Prevent a desired `capturing` flag from masking a dead audio pipeline.
- Keep actual WebSocket writes within a bounded ratio of unique audio frames during gaps, reconnects, rate limits and credential refreshes.
- Recover live delivery without replaying an unordered queue into a new publisher identity.

**Non-Goals:**

- No changes to ASR, RAG, LLM, billing, transcript/SSE behavior, or screenshot behavior.
- No realtime protocol version bump or incompatible message shape.
- No persistence of captured audio.
- No Electron major-version migration in this hotfix.

## Decisions

1. **Aggregate 1,024 samples in the AudioWorklet before transfer.** At common 44.1/48 kHz rates this is approximately 21–23 ms, reducing transfers from about 375 to 43–47 per second per channel while remaining well below the existing realtime frame cadence. A larger 100 ms buffer would reduce overhead further but would add avoidable capture latency; retaining 128-sample transfers preserves latency but reproduces the crash.
2. **Use transferable buffers only for completed batches.** The worklet keeps one bounded in-process accumulator, posts a completed batch with ownership transfer, then allocates the next fixed-size batch. Audio is never persisted.
3. **Throttle renderer health callbacks independently from audio processing.** Audio segmentation and transport continue for every received batch; React-facing meter/health state is emitted at no more than 10 Hz. This avoids UI work affecting the capture fast path.
4. **Recreate the BrowserWindow after `render-process-gone`.** The main process records the reason, destroys the unusable window, and creates a new one unless the app is quitting. Recovery is rate-limited to prevent a permanent startup fault from creating an infinite crash loop.
5. **Keep production release identity unchanged.** Version 0.1.20 uses the existing bundle identifier, Developer ID identity, hardened runtime, `OfferSteady-Notary` profile, and existing production release scripts.
6. **Track reliability separately from the product capture command.** The renderer owns a local five-state reliability machine (`STARTING`, `HEALTHY`, `DEGRADED`, `LOST`, `RECOVERING`) backed by capture, produced-frame, sent-frame and acknowledgement timestamps. The existing backend protocol remains unchanged. A silent source is healthy while worklet callbacks continue; acknowledgement timeouts apply only when frames are pending or have recently been sent.
7. **Use a one-second watchdog with bounded recovery.** A missing capture callback for more than two seconds marks the source lost. A pending WebSocket frame without acknowledgement for more than three seconds marks delivery degraded/lost. Recovery restarts the affected source first and recreates the publisher transport when delivery is stalled. Repeated recovery is rate limited.
8. **Persist only recovery-safe metadata in the main process.** A renderer heartbeat provides the active session-safe identifiers, selected sources and bounded counters/timestamps. `render-process-gone` logs reason, exit code and the last resource snapshot, destroys the dead `webContents`, recreates the window, and supplies a one-shot recovery context. The new renderer re-reads the authoritative binding and starts a fresh publisher; tokens, PCM and transcript content are never checkpointed.
9. **Measure trends at bounded cadence.** Worklet callback/postMessage rates and audio byte counts are accumulated as counters and reported once per minute. Renderer memory/CPU and React render counts are sampled at the same bounded cadence so diagnostics cannot recreate the resource problem they measure.
10. **Diagnose transport amplification beside the send path.** A session-scoped local counter records capture, publisher input, unique sequence, actual WebSocket write, audio/header bytes, ACK, gap, resend, reconnect, queue depth, listener count and bounded duplicate-sequence samples separately for microphone and system audio. It emits one local summary every ten seconds and MUST NOT decide whether a frame is queued, sent, retried, acknowledged, or dropped.
11. **Bound unacknowledged writes per channel.** Normal flushing sends only a small ordered window per logical channel. An ACK advances the window; enqueueing more audio does not bypass it.
12. **Recover one expected sequence at a time.** A `sequence-gap` blocks later writes for that channel and resends only the exact expected frame. Repeated identical gap events are deduplicated and rate limited rather than clearing every sent marker and replaying the whole queue.
13. **Reset when continuity is impossible.** If the expected sequence is no longer present locally, or a bounded resend/circuit-breaker limit is exceeded, the publisher discards stale pending PCM, creates a fresh publisher identity, resets per-channel sequencing and resumes from new live audio. The UI reports recovery; it never claims the discarded interval was delivered.
14. **Reconcile server resume offsets before sending.** The client consumes `resumeOffsets` from the initial connection event, removes acknowledged frames and refuses to replay pending frames whose sequence space cannot match the publisher identity.
15. **Fail closed on amplification.** The desktop stops the affected transport before repeated writes exceed the bounded resend budget. Backend ingress independently closes a connection that exceeds a bounded sequence-gap response budget, protecting commercial capacity even when an old or defective client connects.
16. **Preserve protocol compatibility.** Existing protocol `2.0` events remain valid. Added close reasons and optional recovery metadata are diagnostic; older clients continue to receive existing ACK, gap and degraded events.

## Risks / Trade-offs

- [A 1,024-sample batch adds up to about 21–23 ms before renderer processing] → This is materially lower than ASR/network latency and replaces an unstable 2.7 ms transfer cadence.
- [Automatic renderer recovery could loop if startup itself is broken] → Limit recovery attempts within a rolling time window and leave the window closed after the limit while logging the reason.
- [A throttled meter is visually less granular] → 10 Hz remains smooth for users and does not throttle audio sent to the backend.
- [A short local test may miss a long-run leak] → Add deterministic cadence tests plus a sustained synthetic soak that checks bounded transfer counts and cleanup; retain crash telemetry for real releases.
- [A two-second watchdog can misread legitimate silence as a dead source] → Use raw AudioWorklet callback progress as capture liveness; only require send/ACK progress when speech produced a pending frame.
- [Per-sequence diagnostics could grow for a long interview] → Keep cumulative scalar totals while bounding detailed sequence tracking and duplicate samples; never retain PCM content.
- [Renderer recovery cannot safely reuse a dead renderer's in-memory objects] → Recreate all media, worklet and transport objects from authoritative binding/source metadata; do not reuse tokens or old WebContents.
- [Dropping an unrecoverable pending interval loses a small amount of audio] → Prefer an explicit bounded gap and immediate return to live capture over an infinite resend storm that loses the entire remaining interview.
- [A small in-flight window can reduce peak throughput] → Size the window above normal frame cadence and advance it immediately on ACK; verify p95 delivery while keeping writes bounded.

## Migration Plan

1. Implement and test the worklet batching, UI health throttling, and renderer recovery.
2. Run desktop unit/type/build tests and a sustained synthetic dual-channel soak.
3. Bump desktop version to 0.1.20 and build arm64/x64 release artifacts.
4. Sign, notarize, staple, and validate each DMG.
5. Do not alter the currently published release manifest until the new artifacts pass all verification.
6. Roll back by continuing to serve the prior DMGs; no server or data migration is involved.
7. Before any new public release, pass three real 60-minute capture soaks (system-only, microphone-only, dual-channel). A 120-minute run follows only after all three pass.
8. Release the transport correction as a patch version only after deterministic storm tests, complete desktop/backend suites, production builds and a controlled real ACK test pass.
9. Deploy the backward-compatible Backend guard before publishing desktop 1.1.1, then verify public health, release metadata, signed downloads and a controlled live ACK before broader use.

## Open Questions

None for this focused hotfix.
