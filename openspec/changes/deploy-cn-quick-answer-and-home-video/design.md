## Context

The Global deployment has already exercised an isolated, bounded executor for the synchronous live-answer iterator and content-free stage timing. Chinese production has not received that backend rollout and must not be interrupted while interviews or realtime transports are active. Separately, a supplied 1080p commercial master contains an AAC music/effects track and needs a smaller browser delivery asset on the Chinese public homepage.

The repository is shared by Chinese and Global products, but this release is intentionally limited to Chinese Backend and Web. It does not require a schema migration, vendor change, Prompt change, or a new runtime dependency.

## Goals / Non-Goals

**Goals:**

- Roll out the already-tested bounded live-answer admission path to Chinese production without changing generated content or answer semantics.
- Preserve the commercial film's audio while reducing transfer and decoding cost for desktop and mobile browsers.
- Expose native playback controls while starting muted and avoiding autoplay or eager full-video download.
- Deploy only after Chinese live sessions, active desktop transports and realtime work queues are empty, with an immediate Backend/Web rollback path.

**Non-Goals:**

- Changing model selection, prompts, RAG, ASR, screenshot answering, billing, authentication, Companion behavior or Chinese first-chunk rendering.
- Modifying databases, Redis data, queues, user material or interview records.
- Deploying or restarting Global services.
- Adding autoplay, custom player JavaScript, analytics tracking or additional marketing claims.

## Decisions

### Reuse the tested backend path exactly

Chinese Backend will use the same dedicated bounded executor, admission timeout, bounded event bridge and privacy-safe timing fields already tested in Global. Reusing that implementation avoids creating a Chinese-only concurrency model. The alternative of increasing the shared default thread pool was rejected because unrelated blocking work could still starve live answers and because unbounded admission would only move the queue.

### Keep Chinese stream presentation unchanged

This rollout changes server-side admission only. Chinese Web will retain its existing stream update behavior. The alternative of also importing the Global first-visible-chunk scheduler was rejected because it would expand the behavioral surface of a production performance rollout and make regressions harder to isolate.

### Produce an H.264/AAC fast-start derivative

The web asset will be generated at 720p/30 fps using H.264 video, AAC audio and MP4 fast-start metadata. Explicit video and audio mapping will make the build fail if the master audio stream is missing. The original master remains outside the deployed static directory. Serving the full 1080p/60 fps master was rejected because its extra frames and resolution do not materially improve an embedded homepage presentation, while an audio-less pre-existing derivative is disallowed by the requirement.

### Use a native HTML video player

The homepage will reference the static MP4 and poster using a native `<video>` element with `controls`, `muted`, `playsinline` and `preload="metadata"`; it will not autoplay. Native controls already provide user-controlled volume and fullscreen on supported browsers with less JavaScript and lower failure risk than a custom player.

### Gate the production cutover on observed idleness

Local tests and builds happen without touching production. Production build and replacement occur only after all three signals are zero: live interview sessions with activity inside the configured 20-minute idle window, active desktop transports, and realtime queue/worker activity. A stale database row whose last activity is outside that window is reported but is not treated as a person currently using the product and is not modified by this release. The current release/image identifiers are recorded first. Only Chinese Backend/Web are replaced and each service is health-checked before proceeding. The alternative of a timed deployment without runtime checks was rejected because an interview can still be active during an apparently quiet period.

## Risks / Trade-offs

- [Video audio is accidentally removed during compression] → Explicitly map the master audio stream and verify the output with `ffprobe` before build and deployment.
- [Homepage bandwidth or rendering regresses] → Use a compressed derivative, poster, metadata-only preload, no autoplay and responsive sizing.
- [Executor saturation rejects work too aggressively] → Retain the tested bounded queue and admission timeout, expose timing/saturation telemetry, and preserve the prior image for rollback.
- [Idle metrics race with a newly starting interview] → Recheck immediately before replacement, keep the cutover short, and abort if any signal becomes non-zero.
- [Shared repository changes leak into Global] → Build/deploy only explicitly scoped Chinese images and verify Global health without restarting it.

## Migration Plan

1. Record the current Chinese release, images and health; run read-only activity checks.
2. Generate and verify the web video derivative and poster locally.
3. Run focused and full Chinese Web tests/build plus Backend regression tests and strict OpenSpec validation.
4. Wait until recently active live sessions, desktop transports, realtime workers and queued work are all zero; report but do not mutate stale session rows.
5. Create a versioned Chinese release and rollback tags, then build and replace Backend followed by Web, health-checking after each step.
6. Verify the public homepage asset headers/player markup and Chinese API health; verify Global health remained unchanged.
7. If any check fails, restore the recorded Chinese Backend/Web images and release pointer.

## Open Questions

None. The supplied master, poster, player behavior and Chinese-only deployment boundary are explicit.
