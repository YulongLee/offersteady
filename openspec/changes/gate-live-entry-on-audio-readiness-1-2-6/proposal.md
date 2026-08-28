## Why

Companion 1.2.5 can open and transport both audio sources, but the preparation page treats an opened track as ready even when no real microphone or system-output signal has been observed. Users can therefore enter a live interview with a silent, stale, or low-volume source and only discover the failure after missing the first question.

## What Changes

- Add an explicit, privacy-safe sound check to the preparing workflow for microphone and computer output, with truthful per-source status and actionable retry guidance.
- Gate audio-assisted live entry on fresh evidence that the required sources are open and have produced real signal; manual-only entry remains available without audio permission.
- Keep verified local media warm and transfer it into the live publisher without reopening devices or uploading preparation audio.
- Invalidate readiness after expiry, track end/mute, audio callback stall, permission loss, or output-device changes, and require a fast recheck before live entry.
- Harden low-volume system-audio startup with bounded noise adaptation and pre-speech retention so quiet speech is not indefinitely learned as silence.
- Increment the local acceptance companion to 1.2.6 while preserving the approved 1.2.4 layout, icon, identity, endpoints, and protocol compatibility.
- Non-goals: production deployment, preparation-stage transcription or billing, prompt/model changes, UI redesign, or claiming Intel macOS/Windows physical acceptance from an Apple Silicon test.

## Capabilities

### New Capabilities
- `audio-readiness-entry-gate`: Real-signal preparation checks, expiring readiness, warm source continuity, low-volume first-speech protection, and truthful entry gating for audio-assisted interviews.

### Modified Capabilities
- `streamlined-interview-entry`: Starting an audio-assisted interview now requires fresh source readiness while manual-only entry remains permission-free.

## Impact

- Desktop companion preparation lifecycle, source health, warm handoff, VAD startup policy, version metadata, packaging, and regression tests.
- Web preparation state and start controls, plus compatible protocol fields for content-free readiness evidence.
- Backend binding/runtime readiness exposure may be consumed when available, but this local acceptance scope does not deploy Backend or Web.
- Preparation audio remains memory-only and local; no raw audio, transcript text, secret, or user content is added to diagnostics.
