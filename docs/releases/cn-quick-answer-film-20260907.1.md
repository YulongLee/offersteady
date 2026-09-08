# Chinese Quick Answer and Homepage Film — 2026-09-07.1

## Release

- Version: `cn-quick-answer-film-20260907.1`
- Chinese release path: `/opt/offersteady/releases/20260907-cn-quick-answer-film-1`
- Source baseline: `72c19413d9dca7726117d5b497775844f1a43e31`
- Scope: Chinese Backend and Web only
- Database migrations: none
- Global services: not deployed or restarted

## Changes

- The Chinese live-answer stream now uses the Global-pilot-tested dedicated executor with 8 workers, 8 bounded admission slots and a 16-event per-stream bridge.
- Privacy-safe route-to-admission and admission-to-generator timings are available in runtime metrics. Answer content, model selection, Prompt, RAG, ASR, billing and Chinese first-chunk presentation remain unchanged.
- The Chinese homepage includes the supplied product film with native controls, muted inline playback, metadata preload, poster and no autoplay.
- The web derivative is H.264 1280×720 at 30 fps with AAC stereo audio. It is 2,151,431 bytes and 36.053 seconds; the supplied music/effects audio track is retained.
- `/media/` is served as a direct static path and supports byte-range requests instead of falling through to the SPA or 404 page.

## Validation

- OpenSpec strict validation passed.
- Chinese Web: 47 test files and 355 tests passed; type checking and production build passed.
- Backend focused admission/stream/timing tests passed.
- Backend full regression: 538 passed, 21 skipped, 0 failed. One initial 145 ms scheduling-boundary flake was repeated five times successfully before the clean full run.
- Production candidate built from the exact Chinese source baseline with only the scoped files overlaid; candidate Backend tests, Web test, type check and build passed.
- Both pre-build and pre-cutover gates reported 0 recently active interviews, 0 desktop transports, 0 active queue workers and 0 queued frames. A previously stale live-status row was reported and not modified by the release; normal lifecycle cleanup later reduced the raw live count to zero.
- Public `/healthz` and `offersteady-build.json` report `cn-quick-answer-film-20260907.1`.
- Public MP4 and poster return 200; MP4 byte-range request returns 206 and production download probes as H.264 video plus AAC stereo audio.
- Post-release executor metrics report the configured 8 workers, queue limit 8 and event queue limit 16 with no pending or saturated work.
- Post-release 10-minute Backend/Web error counts were zero.
- Global `/healthz` remained healthy at `global-quick-answer-pilot-20260907.1`.

## Rollback

The pre-cutover images remain tagged as:

- `compose-backend:rollback-before-cn-quick-answer-film-20260907`
- `compose-web:rollback-before-cn-quick-answer-film-20260907`

The preceding source tree remains `/opt/offersteady/app`. During an idle window, retag the two rollback images as `compose-backend:latest` and `compose-web:latest`, then recreate only Backend and Web from `/opt/offersteady/app/infra/compose/docker-compose.foundation.yml` with `/opt/offersteady/app/.env.production` and `--no-build --no-deps --force-recreate`. Do not restart PostgreSQL, Redis, workers, Admin or any Global service, and do not delete volumes.
