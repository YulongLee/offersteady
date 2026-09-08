## 1. Baseline and media preparation

- [x] 1.1 Record local scope and read-only Chinese/Global production health and release baselines without changing a service.
- [x] 1.2 Generate a 720p/30 fps H.264/AAC fast-start web derivative and copy the supplied poster into the Chinese Web static media directory.
- [x] 1.3 Verify the derivative contains video and audio streams, matches the source duration and is smaller than the master.

## 2. Chinese homepage integration

- [x] 2.1 Add a labelled responsive homepage film section with native controls, muted inline playback, metadata preload, poster and no autoplay.
- [x] 2.2 Add regression tests for the player attributes and static asset paths.
- [x] 2.3 Run Chinese Web focused/full tests, type checking and production build.

## 3. Chinese live-answer rollout validation

- [x] 3.1 Confirm the shared bounded live-answer executor and content-free stage telemetry match the Global-tested implementation while Chinese first-chunk presentation remains unchanged.
- [x] 3.2 Run focused and full Backend regression tests for admission, streaming cleanup, timing and existing API behavior.
- [x] 3.3 Run strict OpenSpec validation and inspect the scoped implementation diff for unrelated changes.

## 4. Idle-gated Chinese deployment

- [x] 4.1 Monitor recently active Chinese live sessions, desktop transports and realtime queue/workers until all required signals are zero; report stale rows without modifying them and abort cutover if activity returns.
- [x] 4.2 Record rollback release/images, create a versioned Chinese release, and deploy only Chinese Backend/Web.
- [x] 4.3 Verify Chinese API/Web health, homepage player/assets and compressed media delivery, then confirm Global health and service identity remain unchanged.
- [x] 4.4 Record deployment evidence and rollback instructions in the release documentation.
