## Why

Companion 1.2.4 transports captured audio reliably, but entering a live interview still rebuilds resources that were already opened during preparation, and end-of-speech finalization can leave visible text in an unfinished state longer than the interview workflow tolerates. Version 1.2.5 should make readiness explicit before the interview begins and bound the time from the last meaningful speech to a stable visible transcript without weakening privacy or sentence integrity.

## What Changes

- Add a privacy-preserving preparation standby state that validates and keeps local audio sources warm, establishes expiring publisher readiness, and prewarms provider capacity without uploading, transcribing, storing, or billing preparation audio.
- Promote warmed local sources into the live publisher instead of stopping the preparation monitor and reopening every capture device when the session becomes live.
- Apply source-aware adaptive end-of-speech handling, with a faster system-audio tail and a more conservative microphone tail, while prioritizing terminal frames and bounded recovery.
- Keep provisional transcript text visible while authoritative finalization proceeds; a delayed final result may revise the active block but must not erase confirmed content or block the next turn.
- Record stage-level latency and recovery evidence for start-to-first-ACK and last-meaningful-speech-to-final-render diagnosis.
- Release and locally validate the macOS arm64 companion as version 1.2.5 while preserving the 1.2.4 layout, approved icon, product identity, production endpoint defaults, and protocol compatibility.
- Non-goals: production deployment, persisting preparation audio, starting paid capture before the user starts the interview, changing prompts or answer semantics, or redesigning the companion UI.

## Capabilities

### New Capabilities

- `commercial-realtime-warm-standby`: Preparation readiness, privacy-safe warm promotion, source-aware terminalization, provisional transcript continuity, bounded recovery, and latency evidence for the commercial realtime interview path.

### Modified Capabilities

None.

## Impact

- Desktop companion lifecycle, audio source ownership, publisher transport, endpointing policy, diagnostics, packaging, and regression tests.
- Backend publisher/session readiness, ASR connection lifecycle, terminal commit/finalization, runtime diagnostics, and tests.
- Web live transcript state and rendering tests.
- Shared realtime protocol fields may be extended compatibly; no client secret or model credential is introduced.
- Preparation audio remains local and ephemeral, and existing production endpoints remain unchanged for the local acceptance build.
