## Why

Chinese production still uses the shared live-answer iterator path that can add seconds of admission delay under unrelated API load, while the public homepage lacks an immediately understandable product demonstration. The proven Global quick-answer pilot and the supplied commercial video can address both without changing interview semantics or touching active sessions.

## What Changes

- Apply the already-tested bounded live-answer executor and content-free entry timing to Chinese Backend production.
- Keep the Chinese first-chunk rendering policy unchanged in this rollout; no model, Prompt, RAG, billing, ASR, screenshot or Companion behavior changes.
- Produce a web-optimized H.264/AAC MP4 from the supplied music-and-effects master while preserving its audio track.
- Add a responsive homepage product-film section using static assets and `controls muted playsinline preload="metadata"`, with a poster and user-controlled sound/fullscreen playback.
- Build and test locally, then deploy only Chinese Backend/Web after live interview, desktop transport and realtime queue counts are all zero.
- Preserve the current Chinese release and Backend/Web images for immediate rollback; do not deploy or restart Global services.

## Capabilities

### New Capabilities

- `cn-live-answer-admission-rollout`: Covers safe Chinese rollout of isolated, bounded live-answer admission and privacy-safe stage telemetry.
- `homepage-product-film`: Covers responsive, accessible and bandwidth-conscious delivery of the supplied Chinese product film with its audio retained.

### Modified Capabilities

<!-- No existing main-spec requirement changes. -->

## Impact

- Shared Backend lifecycle, live-answer route and runtime performance telemetry already exercised in Global production.
- Chinese Web landing page, styles, static MP4 and poster assets, plus focused tests.
- Chinese Backend/Web production images and release record only; no database migration and no Global deployment.
