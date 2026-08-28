## Context

The 1.2.6 physical session showed immediate WebAudio callbacks and healthy dual-channel acknowledgements, but system frames remained locally suppressed for roughly 30 seconds while microphone frames were produced during reported user silence. The current segmenter uses source-specific adaptive RMS thresholds, very short attack/minimum windows, and a low-volume system energy-variation bypass. Preparation transfers media handles but not the learned noise baseline, so the live segmenter starts cold. After a desktop terminal, the backend can wait up to eight seconds for provider completion and the Web can only relabel the draft as stale.

The solution spans Desktop, Backend, and Web. Audio and transcript content remain sensitive: preparation PCM must stay local and ephemeral, while diagnostics contain only timing, level, threshold, state, and reason metadata.

## Goals / Non-Goals

**Goals:**

- Reject steady ambient noise and short transients without losing quiet real speech or its first syllables.
- Start capture callbacks immediately and produce the first frame within a bounded interval after actual speech begins.
- Preserve privacy-safe calibration and verified source ownership across preparation-to-live transition.
- Resolve every terminal-admitted visible turn to `final` or explicit `incomplete` within a bounded interval.
- Make the slow stage identifiable without recording PCM or transcript text.
- Ship production-compatible Backend, Web, and signed Apple Silicon companion 1.2.7 with rollback.

**Non-Goals:**

- Uploading or transcribing preparation audio.
- Streaming silence continuously to the provider.
- Changing Qwen model, prompts, answer generation, points, or billing.
- Redesigning approved companion or live workspace layouts.
- Claiming physical Intel macOS or Windows acceptance in this cycle.

## Decisions

### Use calibrated multi-evidence admission instead of a global threshold

Each source keeps a bounded exponentially weighted noise baseline. Start requires source-specific sustained duration plus energy sufficiently above that baseline. Quiet-system admission additionally requires a bounded multi-sample range and ratio so steady digital noise cannot pass merely because three values differ slightly. Microphone admission uses a longer attack/minimum duration than 1.2.6 and requires either normal signal-to-noise evidence or a sustained quiet-speech path. A bounded pre-speech ring retains the leading audio.

Alternative: raise all RMS floors. Rejected because it recreates the missed-quiet-first-speech failure. Alternative: remove local VAD and upload all PCM. Rejected for privacy, bandwidth, provider cost, and billing reasons.

### Transfer calibration metadata, never preparation PCM

Warm handoff carries the live media handle plus content-free noise floor, latest signal time, and calibration sample count. The live segmenter initializes from that bounded calibration when fresh; stale or invalid sources reopen and recalibrate independently. Pre-speech PCM is not transferred or published.

Alternative: reuse the preparation processor and its PCM ring directly. Rejected because it risks publishing pre-live audio and creates duplicate processor ownership.

### Define first-speech latency from actual local admission evidence

Diagnostics distinguish callback start, first above-noise candidate, VAD confirmation, first frame send/ACK, provider first partial, terminal enqueue/ACK, provider completion, recovery, SSE delivery, and browser render. Release gates use actual speech-candidate time rather than interview-entry time, while a separate entry-to-callback metric proves immediate device readiness.

Alternative: infer latency from ten-second aggregate transport logs. Rejected because those logs cannot distinguish user silence from suppressed speech.

### Bound provider finalization and preserve the latest visible partial

Desktop source tails remain short and terminal frames keep priority/explicit acknowledgement. Production uses manual provider commit. Provider completion receives a two-second budget; if it is absent, the backend terminalizes the latest visible partial as `incomplete`, closes only that source generation, and continues later speech. A 2.5-second source watchdog remains an independent safety net. The Web shows `confirming` briefly and then a stable recovered state rather than indefinite transcribing.

Alternative: retry the final provider operation on the same turn. Rejected because it doubles user-visible latency and can mix late provider events with the next utterance.

### Prepare automatically and promote promptly

Binding the companion is the preparation trigger. The companion opens both configured sources, starts callbacks, calibrates locally, and retains only content-free readiness/calibration evidence. The Backend prewarms both provider channels. The Web does not require test playback or prior speech because silence is a valid preparation state and mobile Web clients cannot meaningfully exercise Mac system output. Explicit permission denial, offline devices, or failed capture remain actionable errors, but absence of prior real sound is not a start gate.

While a bound interview remains in preparation, the companion uses a bounded fast control poll so a successful start is observed within 500 milliseconds. On observing `live`, it promotes the already-open sources into the publisher; only post-live admitted PCM is sent. Provider sessions remain lifecycle-persistent and the start operation is best-effort/idempotently prewarmed again without waiting on provider timeout.

The Electron window disables background renderer throttling because the normal product flow places the companion behind the interview browser. Without this setting, Chromium clamps the configured fast control timer to roughly one second and can also delay renderer-owned audio work despite the foreground configuration being correct.

Alternative: require the user to play a sample and speak before every interview. Rejected because it creates a fragile hard gate and is unusable from mobile preparation. Alternative: upload preparation audio to keep the full publisher hot. Rejected because it violates the privacy boundary and can create pre-interview transcripts or billing.

### Pin a live desktop binding and make reconnect state truthful

The companion includes its current session and binding identifiers in active-connection polls. While that binding remains active for the same registered device generation, the Backend returns it even if another historical binding has a later timestamp. A new account or session cannot silently stale a device binding whose session is already live; the bind request fails with an explicit conflict. Once the pinned session ends, becomes stale, changes device generation, or the publisher receives an authoritative terminal session error, the pin is released and normal binding discovery resumes.

Initial publisher construction is a start transition, not a reconnect. The companion keeps the existing live/capturing control state while opening the initial transport and sources. It publishes `reconnecting` only after a previously healthy publisher or source enters recovery. Missing health for one source during bootstrap falls back to the live control state; explicit source `reconnecting`, permission failure, or transport loss remains visible.

Alternative: always follow the most recently created binding. Rejected because a second page/account can tear down a healthy interview publisher. Alternative: hide every reconnect warning. Rejected because real transport recovery and audio gaps must remain visible.

### Roll out compatibility-first

Backend deploys first with old-client compatibility, then Web readiness/terminal presentation, then the signed 1.2.7 companion. Existing database schema and protocol required fields do not change. Optional diagnostics and calibration fields remain backward compatible.

## Risks / Trade-offs

- [A very quiet speaker may need longer admission] → keep calibrated quiet-speech path and pre-speech retention; validate against synthetic quiet speech.
- [Transient noises can resemble speech energy] → require sustained multi-evidence admission and suppress low-evidence short provider results.
- [Two-second provider completion budget can yield incomplete text] → preserve the newest partial, label recovery truthfully, and reopen only the affected source.
- [Production feature flags may differ from repository defaults] → inspect resolved container configuration after deploy and record only non-secret values.
- [Cross-platform audio levels differ] → keep thresholds source-relative and run automated packages for all targets, but report physical acceptance only for Apple Silicon.
- [A stale pin could block the next interview] → Backend validates session state, binding status, device generation and identity on every poll; terminal publisher errors clear the client pin.

## Migration Plan

1. Add deterministic Desktop regressions for steady noise, transients, quiet speech, warm calibration, first-frame timing, and bounded tails.
2. Implement Desktop calibration transfer, admission, diagnostics, and version 1.2.7.
3. Add Backend regressions for manual commit, two-second provider timeout recovery, no final retry, source isolation, and bounded watchdog.
4. Add Web regressions for automatic preparation entry and stable terminal/incomplete presentation.
5. Run full tests, typechecks, builds, strict OpenSpec validation, and synthetic end-to-end timing checks.
6. Record the production rollback baseline; deploy Backend, verify, then Web, verify.
7. Build/sign/install/open the Apple Silicon 1.2.7 companion and retain the current application as rollback.
8. Verify a second binding cannot displace an active live interview, then repeat 1.2.9 local acceptance with a pinned session and truthful startup state.

Rollback restores the previous Backend/Web images or commit and the backed-up companion independently. No database migration is involved.

## Open Questions

None blocking. Physical tuning remains subject to the user's post-install acceptance session; thresholds are implementation configuration, not fixed product promises.
