## Context

The production realtime path already streams microphone PCM revisions every 100 ms and normally publishes a provider final 0.44–0.95 seconds after the desktop emits a terminal frame. Production evidence nevertheless contains visible partial segments that never receive a terminal event. Two independent causes amplify the symptom: microphone endpointing treats any RMS above a low continuation threshold as indefinitely active, and a suppressed final reconciles Redis transcript state without publishing the corresponding `transcript-updated` event. The production Compose configuration also leaves the existing source watchdog at its disabled code default, while the web waits eight seconds before presenting a stale partial as incomplete.

The change spans the Electron companion, FastAPI realtime service, Redis event stream, web presentation, and production configuration. It must remain compatible with current protocol v2 clients, preserve source isolation, avoid answer or billing side effects for incomplete/suppressed segments, and never persist raw audio or transcript text in diagnostics.

## Goals / Non-Goals

**Goals:**

- Finalize ordinary microphone speech within a 1.5 second p95 budget after speech energy falls back to the ambient range.
- Prevent steady residual energy after a louder utterance from refreshing the speech timer indefinitely.
- Publish a monotonic terminal event whenever a visible partial is suppressed, superseded, or abandoned.
- Enable a bounded four-second backend recovery path in production and a matching four-second web presentation guard.
- Ship the companion behavior as patch version 1.1.5 for macOS and Windows.

**Non-Goals:**

- Replace Qwen realtime ASR, the WebSocket v2 transport, or dual-channel capture.
- Add a native or cloud VAD dependency in this patch.
- Infer that an incomplete transcript is provider-final or use it to trigger answers, context, usage, or billing.
- Store PCM, transcript text, API keys, or access tokens in diagnostics.

## Decisions

### Use a peak-relative release gate in the existing adaptive endpoint controller

The microphone segmenter will track the turn peak and require continuation energy to clear both the adaptive ambient threshold and a bounded fraction of the turn peak. Energy that falls sharply toward the ambient range enters the existing tail state instead of indefinitely refreshing `lastSpeechAtMs`. The microphone tail is reduced from 700 ms to 500 ms; the existing start threshold remains the tail-resume threshold so a real resumed utterance cancels finalization.

This keeps the change dependency-free and deterministic. Merely lowering the tail timeout was rejected because it does nothing when residual noise continuously resets the timer. Adding WebRTC or neural VAD was rejected for this patch because it expands binary size, platform packaging risk, and model governance without first exhausting the existing signal envelope.

### Publish terminal reconciliation as part of suppressed-final handling

When a final provider result is suppressed as empty, filler, repetitive, or duplicate, the backend will convert any visible same-segment partial to a final display record and publish a `transcript-updated` terminal event. The event preserves the visible stable text but bypasses context insertion, question detection, usage duplication, answer generation, and billing.

Persisting the reconciliation without an event was rejected because the web consumes the bounded event stream and cannot observe a Redis-only record mutation until an unrelated rehydrate.

### Terminalize a partial superseded by a newer segment on the same source

Before tracking a new non-final segment for a source, the backend will mark an older active segment from that source incomplete and publish a terminal event without closing the healthy source connection. This covers a missing desktop terminal while allowing the new segment to proceed. A provider-final or explicit terminal frame still remains authoritative.

Tracking only one source-level watchdog record was rejected because overwriting it with a newer segment silently abandons the older partial.

### Enable the source watchdog at the production Compose boundary

The shared production Compose definition will explicitly default the watchdog to enabled with a four-second deadline and 500 ms poll interval. Application configuration keeps the independent feature flag for rollback. The watchdog closes only the affected ASR source and emits an `incomplete` terminal event with no business side effects.

### Align the web stale presentation guard with the recovery budget

The web will stop the animated transcribing state after four seconds without a revision, matching the backend recovery deadline. This is presentation-only and does not promote the segment to provider-final.

### Prevent initial snapshot timeout reconnect storms

Production validation exposed a recovery-loop regression: the browser allowed only two seconds for the first complete SSE snapshot and reset its reconnect attempt after every successful HTTP fallback snapshot. A temporarily slow initial snapshot therefore caused an immediate reconnect loop even though the fallback kept the visible state recoverable.

The browser will allow five seconds for the first complete SSE snapshot. A successful fallback snapshot will update the page but will not reset the stream reconnect attempt; only a successfully parsed stream snapshot resets backoff. This bounds retry load while preserving automatic recovery and does not change ASR, transcript, or billing behavior.

## Risks / Trade-offs

- [Peak-relative release can split speech after a very loud syllable followed by unusually quiet speech] → Cap the release threshold, retain a 500 ms tail, allow strong speech to resume the same segment, and cover quiet/continuous speech with synthetic tests.
- [A four-second watchdog can race a late terminal] → Keep revision monotonicity and the existing fresh-frame guard; terminal states cannot be reopened by late partials.
- [Superseded incomplete events could duplicate a late final] → Use the stored transcript revision and terminal-state checks so the event is idempotent and later stale revisions cannot replace it.
- [Production watchdog increases source reconnects during provider stalls] → Keep the flag independently reversible and monitor `incompleteRecoveries`, reconnects, queue depth, and terminal latency.
- [A slow or oversized initial SSE snapshot can trigger a reconnect storm] → Use a five-second first-snapshot budget and retain exponential backoff across HTTP fallback recovery until SSE itself is healthy.

## Migration Plan

1. Add regression tests and implement backend/web behavior with protocol compatibility.
2. Implement and benchmark the desktop endpointing adjustment, then increment the companion to 1.1.5.
3. Run focused and broader backend, web, protocol, and desktop tests plus type checks and production builds.
4. Commit one tested source revision, retain rollback images/artifacts, and deploy backend before web.
5. Publish immutable macOS and Windows 1.1.5 companion artifacts and update the production manifest only after verification.
6. Verify health endpoints, asset versions, watchdog configuration, and a live privacy-safe timeline. Roll back individual feature flags or prior images/manifests if terminal errors or false splits regress.

## Open Questions

None.
