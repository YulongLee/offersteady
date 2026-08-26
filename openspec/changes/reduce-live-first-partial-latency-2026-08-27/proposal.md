## Why

The 1.1.7 production acceptance test proved that audio delivery is now stable, but the first visible partial still takes about 4.7 seconds at p50 and 6.2 seconds at p95. Transport, Redis, SSE, and React are fast; the remaining delay is dominated by lazy provider connection startup, overly late first effective partials for system audio, and incomplete first-visible telemetry.

## What Changes

- Prewarm one reusable Qwen Realtime ASR connection per active interview channel before the first speech frame, without sending or persisting audio.
- Preserve the existing 100 ms audio cadence while prioritizing the first speech payload and keeping later append work non-blocking.
- Add a bounded first-partial watchdog and content-free channel metrics that distinguish provider cold start, audio accumulation, and browser delivery.
- Correct first-visible-partial measurement so it records the first painted revision of each utterance rather than a later sampled revision.
- Keep the current manual endpointing and finalization semantics; do not trade final accuracy for an earlier placeholder transcript.

## Capabilities

### New Capabilities

- `commercial-first-partial-latency`: Defines provider prewarming, early partial delivery, truthful first-visible measurement, and production latency gates for both logical audio channels.

### Modified Capabilities

None.

## Impact

- Affects the Backend realtime speech service, DashScope realtime gateway, realtime metrics, Web delivery acknowledgements, and their tests.
- Does not change protocol 2.0, the desktop package version, prompts, model selection, transcript persistence, billing semantics, or raw-audio privacy policy.
- Adds at most two idle provider WebSocket connections per active interview and closes them through existing session idle/end cleanup.
