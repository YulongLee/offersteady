## Why

Production traces show that normal provider finalization completes in under one second after a terminal audio frame, but microphone background noise can postpone desktop end-of-speech detection and some partial transcript segments can remain without a terminal update. This leaves users seeing “转写中” long after they stop speaking, which is incompatible with a commercial realtime interview experience.

## What Changes

- Make microphone endpointing resilient to steady low-energy noise while preserving continuous speech and avoiding aggressive false splits.
- Guarantee that every published partial segment reaches either a provider-final or explicit incomplete terminal state within a bounded time.
- Enable and configure the backend source-turn watchdog in production, with terminal updates that do not trigger answers or billing.
- Shorten the web presentation fallback for abandoned partials while preserving the distinction between provider-final and incomplete recognition.
- Add synthetic regression coverage and production-safe latency diagnostics; raw audio and transcript text remain unpersisted by diagnostics.
- Increment the desktop companion patch version and publish updated macOS and Windows artifacts.

## Capabilities

### New Capabilities

- `bounded-live-speech-finalization`: Defines noise-resilient end-of-speech detection, bounded partial terminalization, and measurable speech-stop-to-final behavior across desktop, backend, and web.

### Modified Capabilities

None.

## Impact

- Desktop audio segmentation and companion release metadata under `apps/desktop`.
- Backend realtime source-turn watchdog configuration and terminal reconciliation.
- Web conversation transcript presentation timing.
- Realtime regression tests, deployment configuration, release artifacts, and operational documentation.
- No API-breaking change, no client-side service keys, and no new persistence of audio or transcript content.
