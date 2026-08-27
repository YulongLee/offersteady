## Why

Production users can enter a live interview while desktop capture, provider sessions, or browser delivery are not actually ready, causing the first utterance to be delayed or lost. A slow or missing provider completion can also block one source for seconds and retry without the complete utterance, leaving the UI stuck or producing incomplete text.

## What Changes

- Introduce an authoritative, per-source readiness contract covering desktop transport, capture availability, provider readiness, and browser event delivery.
- Rewarm active interviews after backend restart or desktop reattachment and prevent a global `capturing` state from masking an unavailable microphone or system-audio source.
- Extend source-turn terminalization so the `committing` state remains bounded and cannot block subsequent audio ingestion.
- Retain only a bounded, in-memory copy of the active utterance so a provider reconnect can retry the complete utterance once; never persist PCM or include it in diagnostics.
- Complete content-free first-visible and terminal timing telemetry and add cold-start, restart, missing-completion, dual-channel, and continuous-session regressions.
- Publish the tested desktop behavior as companion version 1.2.2 without changing the existing layout, branding, icons, or production endpoint.

## Capabilities

### New Capabilities

- `commercial-live-readiness`: Defines when an interview is truthfully ready for immediate microphone and system-audio capture, including restart and reattachment recovery.
- `bounded-terminal-recovery`: Defines non-blocking terminal admission, bounded provider completion, complete-utterance recovery, and monotonic visible terminal states.

### Modified Capabilities

None.

## Impact

- Desktop source-health reporting, capture lifecycle, protocol metadata, package version, and macOS local build.
- Backend live-session start/reattachment, Qwen realtime ASR lifecycle, source worker state, ephemeral audio buffering, watchdog behavior, and privacy-safe metrics.
- Web live readiness projection and transcript delivery telemetry while preserving the current visual layout.
- Protocol, backend, desktop, Web, AI evaluation, soak, and OpenSpec verification.
- No client-side service keys, no raw-audio or transcript persistence, no automatic answer generation, and no production deployment in this change's local acceptance phase.
