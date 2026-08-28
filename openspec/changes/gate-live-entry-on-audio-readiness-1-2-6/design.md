## Context

The preparing desktop already opens microphone and system-audio streams and 1.2.5 can transfer those stream handles into the live publisher. Its health model, however, reports an opened live track separately from whether meaningful signal has ever crossed the local detector. The Web preparation page does not expose a deliberate sound-test gate, and the desktop readiness evidence can remain apparently healthy after a track stalls or an output route changes. Physical 1.2.5 evidence also showed a 30-second interval between session observation and the first system frame while transport ACK, reconnect, gap, and queue metrics remained healthy.

Preparation audio is sensitive. Readiness checks must stay local and memory-only, and publisher authorization and ASR transcription remain live-only. The current production Web/Backend are older than the local 1.2.5 source, so the first acceptance target is a signed Apple Silicon companion that preserves production endpoint compatibility and can expose truthful preparation health without silently claiming the undeployed Web gate is active.

## Goals / Non-Goals

**Goals:**

- Distinguish track-open readiness from fresh real-signal evidence for each audio source.
- Give the user an explicit local microphone/system sound check and actionable failure state before live entry.
- Preserve verified stream ownership across preparing-to-live and invalidate stale readiness on route/track/callback failures.
- Prevent quiet system speech from being indefinitely absorbed into an adaptive noise floor and retain the first syllables.
- Keep manual-only entry independent from audio permissions.
- Preserve the approved companion layout, icon, identity, endpoints, protocol, and privacy boundary.

**Non-Goals:**

- Uploading, transcribing, storing, or billing preparation audio.
- Redesigning the companion or Web live workspace.
- Changing prompts, answer behavior, model selection, or billing.
- Deploying production Backend/Web or claiming cross-platform physical acceptance in this local cycle.

## Decisions

### Represent readiness as fresh evidence, not a green track

Each local source health record will distinguish `track-live` from `signal-detected`, retain a content-free `lastSignalAtMs`, and expose whether the evidence is fresh. A source is audio-ready only when its track is live, callbacks are advancing, and a signal above the source-specific verification threshold was observed inside the readiness lifetime. Track end/mute, callback stall, context failure, permission loss, or route change invalidates readiness immediately.

Alternative considered: gate only on permission and `MediaStreamTrack.readyState`. Rejected because that is the current false-positive condition and cannot prove that audible input reaches the processor.

### Keep the check explicit and privacy-local

The companion preparation surface will present microphone and computer-output check status using the existing cards and layout. It will instruct the user to speak and play a short voice sample, show live level/status, and make retry available. No preparation PCM leaves the process. The Web start gate will consume safe source-health/readiness state when that compatible Web is deployed; the local 1.2.6 package truthfully reports readiness but cannot alter the already-deployed production Web bundle.

Alternative considered: upload a preparation sample to ASR for proof. Rejected because it introduces transcription, privacy, cost, and consent before the interview starts.

### Transfer only fresh verified sources and revalidate at live transition

The one-shot warm handoff will carry content-free readiness evidence with the media handle. Live transition performs a fast track/context/freshness check; a valid source is promoted, while an invalid source independently falls back to reopen/recovery. No preparation samples or pre-speech buffer are transferred into the live publisher.

Alternative considered: keep preparation and publisher processors attached simultaneously. Rejected because duplicate media owners and callbacks previously caused route-switch and resource problems.

### Bound adaptive system noise learning and preserve first speech

System startup will use a conservative low floor and ceiling, bounded noise-floor learning, and a short rolling pre-speech buffer. Sustained low-level energy will not be allowed to raise the start threshold indefinitely. After speech begins, existing source-aware tail and terminal priority remain unchanged.

Alternative considered: continuously upload all live PCM and delegate VAD entirely to the provider. Deferred because it materially increases bandwidth/provider usage and requires a broader Backend protocol and billing review.

### Use an expiring readiness lease

Signal readiness expires after 120 seconds and is invalidated by source lifecycle events. Live entry performs a fast recheck instead of assuming an old green state. The expiry is long enough for normal preparation but short enough to avoid treating an unplugged or rerouted device as ready.

## Risks / Trade-offs

- [A quiet but usable source may not cross the verification threshold] → Use source-specific low verification floors, visible level guidance, and retry rather than silently waiting in live mode.
- [Music can pass a system sound check although speech recognition quality differs] → Instruct the user to use a bundled/spoken voice sample and treat readiness as transport proof, not ASR accuracy proof.
- [Readiness may expire while the user reads preparation material] → Refresh on new local signal and show a clear recheck action without reopening a healthy source.
- [Production Web cannot enforce a newly implemented local gate until deployed] → Keep the companion state truthful, test the compatible Web locally, and report local versus production acceptance separately.
- [Lower VAD threshold can increase silent/noise frames] → Keep bounded hysteresis, minimum speech duration, terminal semantics, and transport metrics; do not remove local gating entirely.

## Migration Plan

1. Add readiness-state and low-volume detector regressions before changing behavior.
2. Implement content-free source readiness and invalidation in the preparation monitor and warm handoff.
3. Add the explicit check status and compatible Web start gate without changing the approved layout.
4. Increment to 1.2.6 and run focused/full desktop and Web validation plus strict OpenSpec validation.
5. Build, sign, back up 1.2.5, install, and open the Apple Silicon local acceptance app.

Rollback restores the backed-up 1.2.5 application. Backend/Web deployment remains a separately authorized operation.

## Open Questions

None. The user explicitly approved preparation-stage real-signal verification, gated audio entry, warm continuity, and local retesting.
