# Release 1.2.2

Release 1.2.2 is a local-acceptance candidate focused on immediate live readiness and bounded end-of-speech recovery. It preserves the 1.2.1 layout, approved icon, product name, bundle identifier `com.offersteady.companion`, production endpoints, and realtime protocol `2.0`.

## Scope

- Rewarm microphone and system Qwen sessions when a desktop attaches to an already-live interview after a backend restart.
- Report microphone and system capture readiness independently; a connected transport no longer implies both sources are ready.
- Keep provider-final turns under the four-second source watchdog instead of dropping supervision at terminal admission.
- Retain only one capped, process-local PCM utterance per active source segment so one retry can replay the complete utterance rather than the terminal tail.
- Clear ephemeral PCM on final, incomplete, pause/end/session reset, overflow, or TTL expiry. PCM is never persisted or emitted in telemetry.
- Preserve subsequent bounded source frames while provider completion is pending and show preparing/degraded state through the existing Web presentation.

## Local Acceptance Gates

- Start click to authoritative live-ready: P95 <= 2 seconds; provider failure becomes explicit within 4 seconds.
- Speech start to first visible partial: P50 <= 1.5 seconds and P95 <= 3 seconds on recognizable authorized speech.
- Speech end to final/incomplete: P95 <= 1.5 seconds, P99 <= 3 seconds, and no unlabelled transcribing state after 4 seconds.
- Microphone and system audio are verified independently across cold start, backend restart, page refresh, consecutive utterances, and source failure.
- Diagnostics retain counts and timestamps only; no raw audio or transcript text is stored.

## Release State

This document records a local candidate only. Production remains on 1.2.1 until the user completes local acceptance and explicitly authorizes a separate rollout.
