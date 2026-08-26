## Context

The live incident shows the Electron process and shared WebSocket remain alive, but macOS ends the ScreenCaptureKit loopback track. `recoverSource` destroys the old runtime and performs one immediate reopen. If that reopen races the route transition, no runtime remains to own the recovery timer, leaving system capture permanently stopped. Resends also overwrite the diagnostic last-sent value with an older sequence.

## Goals / Non-Goals

**Goals:**

- Recover system audio after transient output-route changes without recreating the publisher.
- Recover microphone capture onto the current default input when a selected headset disappears.
- Keep microphone capture, sequence continuity, and bounded resource ownership intact.
- Provide deterministic regressions and a locally testable 1.1.8 build.

**Non-Goals:**

- No Backend protocol, ASR, billing, transcript, permission, or raw-audio persistence changes.
- No promise of recovery when macOS permanently exposes no capturable output.

## Decisions

### Keep recovery ownership on the publisher

The publisher will schedule serialized system-source attempts independently of a media runtime. A runtime-local timer was rejected because it disappears exactly when track recovery fails.

### Use bounded backoff and latest-intent convergence

Immediate failure will schedule short bounded retries. One in-flight recovery per channel and a generation token prevent overlapping opens or a late attempt attaching after stop. Infinite retries were rejected because they can leak prompts and resources.

### Fall back from a removed microphone identity

An ended or watchdog-lost microphone track will reopen the operating-system `default` input instead of retrying the stale headset device ID. Explicit user device changes retain the requested identity. Both paths use bounded retries so a macOS route transition cannot turn one failed open into a permanent outage.

Because Chromium's virtual `default` route can continue pointing at a removed Bluetooth device, fallback enumerates current physical inputs, excludes the ended track identity, prioritizes the built-in microphone, and bounds every individual media request. A request that resolves after its timeout is closed immediately so recovery cannot leak tracks.

### Preserve sequence and make diagnostics monotonic

Source reopening will reuse the publisher sequencer. Diagnostic last-sent values will be maxima, while resend counts separately describe older-frame transmission. Resetting sequence or publisher identity was rejected because the Backend receipt is authoritative.

### Require explicit terminal acknowledgement across resume

A Backend resume offset proves that a sequence was observed, but a terminal receipt can exist before its bounded worker admission completes. The Desktop therefore retains `isFinal` envelopes even when their sequence is at or below the resume offset and retires them only after `terminal-accepted`. The Backend re-admits an older terminal whose terminal id is not known as accepted; an already-admitted or provider-final terminal remains idempotent.

### Decouple transport replacement from media ownership

A sequence-gap transport replacement will gate publication but keep healthy microphone and system runtimes attached. The sequencer is realigned from the replacement publisher's authoritative offsets before callbacks can publish again. Stopping and reopening both media sources was rejected because an unrelated transport fault can then lose ScreenCaptureKit and microphone capture permanently.

## Risks / Trade-offs

- [macOS remains unsettled longer than the retry window] → Use several bounded attempts and leave only the affected channel degraded.
- [Stop races an open attempt] → Gate attachment with a recovery generation and close losing media immediately.
- [Multiple ended/watchdog signals overlap] → Single-flight recovery converges on one supervisor.

## Migration Plan

Add regressions, implement recovery and diagnostics, bump to 1.1.8, run full Desktop verification, build/install locally, then perform a physical headset-removal acceptance test. Rollback remains the signed 1.1.7 artifact.

## Open Questions

None.
