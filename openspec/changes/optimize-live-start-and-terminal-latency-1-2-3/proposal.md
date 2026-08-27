## Why

Authorized live testing of the 1.2.2 candidate still shows two commercial blockers: a newly entered interview can wait many seconds before the first computer-audio transcript appears, and a stopped utterance can remain visibly transcribing or incomplete long after speech has ended. Transport and normal provider completion are usually fast, so the patch must bound desktop endpointing and browser delivery instead of hiding the delay behind longer retries.

## What Changes

- Make microphone and system-audio startup produce usable speech frames promptly after capture is ready, while preserving silence as a healthy state.
- Add source-specific, noise-resilient release logic and an explicit last-meaningful-speech deadline so residual system audio cannot keep one utterance open until the hard-turn limit.
- Bound terminal confirmation independently from terminal admission and preserve one monotonic final or incomplete result without blocking the following utterance.
- Stabilize the browser session SSE initial snapshot and reconnect lifecycle so partial and terminal transcript events are delivered without repeated five-second fallback loops.
- Distinguish speaking, transcribing, confirming, final, and incomplete presentation states using the existing layout.
- Add content-free measurements from last meaningful speech through desktop terminal, provider completion, SSE delivery, and browser paint.
- Increment the companion patch version from 1.2.2 to 1.2.3 while preserving layout, icons, signing identity, bundle identifier, and production endpoint defaults.
- After explicit rollout approval, apply the shared endpointing behavior to macOS ARM64, macOS Intel x64, and Windows x64, publish all three 1.2.3 artifacts atomically, and deploy the compatible Backend/Web changes before switching the production manifest.

## Capabilities

### New Capabilities

- `immediate-live-transcript-start`: Defines bounded capture-to-first-visible behavior, ASR readiness, and stable initial browser delivery for newly entered interviews.
- `bounded-visible-turn-completion`: Defines noise-resilient speech release, bounded provider terminalization, monotonic browser presentation, and end-to-end stop latency measurement.

### Modified Capabilities

None.

## Impact

- Desktop speech segmenter, source health/diagnostics, regression tests, package metadata, and the macOS ARM64, macOS Intel x64, and Windows x64 release matrix.
- Backend source-turn supervision, provider finalization deadlines, event-stream initial delivery, privacy-safe timing metrics, and regressions.
- Web SSE subscription/recovery, transcript presentation state, reducer tests, and existing status copy without layout changes.
- OpenSpec artifacts, runtime documentation, release notes, local acceptance evidence, production release manifest, and rollout verification.
- No raw audio or transcript text persistence, no client-side API keys, and no implicit answer generation or billing.
