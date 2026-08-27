## Context

The production path is Electron source capture -> multiplexed WebSocket v2 -> per-source FastAPI worker -> persistent Qwen realtime ASR -> Redis cursor stream -> browser reducer. Authorized 1.2.2 testing showed healthy audio acknowledgements and zero backend queue depth, but system audio produced no effective frames during the opening interval, browser first-visible latency reached 16.9 seconds, and the browser repeatedly entered five-second SSE timeout/fallback cycles. Normal terminal frames complete quickly after admission, yet residual system energy can postpone desktop terminal creation and exceptional provider completion can remain pending behind an eight-second provider wait.

The existing UI, protocol 2.0 compatibility, source isolation, explicit-only answer generation, and privacy rule that PCM and transcript content never enter diagnostics must remain unchanged.

## Goals / Non-Goals

**Goals:**

- Deliver recognizable microphone and system audio promptly after a newly entered interview becomes capture-ready.
- Bound the interval from last meaningful speech to desktop terminal intent even under residual system noise.
- Bound terminal admission through provider completion or explicit incomplete recovery without blocking subsequent speech indefinitely.
- Keep the browser session stream stable and make the first authoritative snapshot available promptly.
- Measure the user-perceived stop boundary rather than starting terminal latency only after the desktop has already waited.
- Ship companion 1.2.3 with the same shared endpointing behavior on macOS ARM64, macOS Intel x64, and Windows x64, with no visual or identity regression.

**Non-Goals:**

- No provider/model migration, cloud server-VAD rollout, neural VAD dependency, automatic answer generation, Windows ARM64/Linux support, or UI redesign.
- No persistence of audio, transcript text, credentials, or personal material in diagnostics.
- No promise to classify speech semantics from continuous music; the endpoint remains an energy-based bounded controller.

## Decisions

### Add a source-specific meaningful-speech release deadline

The segmenter will retain the existing adaptive attack and 500 ms normal silence tail. Both sources will track turn peak and last meaningful speech. System audio receives a bounded peak-relative release gate, and an active turn whose energy remains below its meaningful threshold will terminalize within a source-specific maximum release window. Strong resumed speech cancels the tail. The hard twelve-second turn limit remains a final safety boundary.

Only lowering the silence duration was rejected because residual noise can continuously refresh the timer. Adding a native or neural VAD was rejected for this patch because it creates new cross-platform packaging and governance risk before the deterministic controller is correctly bounded.

### Separate terminal admission, user-visible confirmation, and hard recovery

Terminal admission remains immediate and idempotently acknowledged. A committing turn remains supervised. Normal provider completion keeps its existing fast path; a short user-visible confirmation budget is recorded separately from the hard provider timeout. At the source watchdog deadline the latest stable partial becomes one monotonic incomplete terminal, the affected provider source is recreated, and subsequent queued speech proceeds. Late events from the retired segment cannot reopen it.

Blindly lowering the provider socket timeout was rejected because a transient slow completion should not discard a stable partial or recreate both sources. Waiting the full provider timeout was rejected because it exposes implementation recovery time as a user spinner.

### Make SSE initial delivery cheap and reconnect ownership stable

The session stream will emit its first authoritative materialized state without waiting for avoidable secondary work. The browser keeps one leader-owned subscription, does not reset reconnect backoff after an HTTP fallback, and treats only a successfully parsed stream snapshot as stream recovery. Final and incomplete transcript events remain non-coalescible terminal work.

Increasing the first-snapshot timeout was rejected because it would hide the observed five-second loop while preserving unacceptable first-visible latency.

### Present a bounded confirming state in the existing transcript row

The existing transcript metadata area will distinguish active transcription from a terminal intent awaiting provider confirmation. Confirming is bounded by backend state; it becomes final or incomplete and never continues indefinitely. No structural layout, icon, or new control is introduced.

### Measure from last meaningful speech

Desktop diagnostics will carry content-free `lastMeaningfulSpeechAtMs` and terminal timestamps. Backend trace aggregation will derive last-meaningful-speech-to-terminal, terminal-to-provider-final, SSE, and browser render distributions per source. Existing `speechEndToFinal` remains for compatibility but is no longer the sole acceptance metric.

### Keep endpointing platform-neutral and release all supported targets together

Attack, peak-relative release, last-meaningful-speech deadlines, protocol envelopes, and Web/backend terminal behavior remain in the shared TypeScript/protocol/server path. Platform adapters are responsible only for producing normalized PCM: ScreenCaptureKit on both macOS architectures and WASAPI loopback on Windows x64. The release gate builds and inspects all three artifacts; macOS artifacts require Developer ID, notarization, staple, Gatekeeper, and architecture verification, while the Windows installer retains its truthful unsigned status until an Authenticode certificate exists. The production manifest switches all three supported targets in one publication.

## Risks / Trade-offs

- [A release deadline can split an unusually quiet continuation] -> Keep a 500 ms tail, require peak-relative evidence, cap thresholds, and cover short pauses plus loud-to-quiet speech in regression fixtures.
- [Continuous music cannot be classified perfectly by RMS] -> Bound segments and label incomplete recovery truthfully; keep future pluggable VAD evaluation outside this patch.
- [A watchdog can race a late provider final] -> Use segment identity, source generation, monotonic revisions, and terminal precedence.
- [SSE optimization can alter cursor behavior] -> Preserve cursor advancement across coalesced partials, never coalesce terminal events, and test reconnect/replay/fallback explicitly.
- [More timing fields increase telemetry volume] -> Emit timestamps and counters only, sample browser acknowledgements, and exclude content and PCM.

## Migration Plan

1. Add failing desktop, backend, and Web regressions for startup, noisy release, committing timeout, and SSE reconnect ownership.
2. Implement backward-compatible optional diagnostics and source behavior behind existing endpointing/watchdog controls.
3. Increment desktop metadata to 1.2.3 and update release/evaluation documentation.
4. Run focused and full tests, typechecks, builds, strict OpenSpec validation, and a bounded local soak.
5. Build and start the local signed macOS 1.2.3 app against the current production endpoint for user acceptance.
6. After explicit rollout approval, build and verify macOS ARM64, macOS Intel x64, and Windows x64, then publish all three artifacts atomically.
7. Deploy compatible backend/Web before exposing the 1.2.3 manifest. Rollback restores the prior service commit and the 1.2.1 production manifest.

## Open Questions

None blocking implementation. Real speech acceptance will determine whether the system release window requires later canary tuning.
