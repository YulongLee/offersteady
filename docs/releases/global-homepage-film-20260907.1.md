# Global homepage product film 2026-09-07.1

- Host: `47.84.65.103`
- Release: `global-homepage-film-20260907.1`
- Planned release path: `/opt/offersteady-global/releases/20260907-global-homepage-film-1`
- Baseline: `/opt/offersteady-global/releases/20260907-global-quick-answer-pilot-1`
- Scope: Global Web only
- Database migrations: none
- Backend, Admin, worker, PostgreSQL, Redis, Companion and China deployment changes: none

The release adds the English OfferSteady product film to the international homepage. The native player starts muted, does not autoplay, exposes browser controls, supports inline mobile playback, and preloads metadata only. The versioned 1080p H.264/AAC MP4 is 36.05 seconds and approximately 4.6 MB; its AAC music and sound-effects track is preserved.

## Verification

- Source MP4 and deployed copy have matching SHA-256 digests.
- Global Web: 54 tests passed; 660-entry English-copy audit, typecheck, and production build passed.
- OpenSpec strict validation passed.
- Before cutover: recent live interviews 0, active desktop transports 0, active realtime workers 0, and queued frames 0.
- Production MP4 returned `200 video/mp4`, the poster returned `200 image/jpeg`, and a 1,024-byte range request returned `206` with the expected `Content-Range` and `Accept-Ranges` behavior.
- Production media SHA-256 digests match the approved local assets; the homepage bundle contains the new heading and versioned MP4/poster paths.
- The build marker reports `global-homepage-film-20260907.1`; Global and China public health checks pass.
- Only Global Web was recreated. Global Backend, Admin, PostgreSQL, and Redis retained their container IDs, start times, and zero restart counts; the Global Web error count after deployment was zero.

## Rollback

The preceding release remains `/opt/offersteady-global/releases/20260907-global-quick-answer-pilot-1`. Before cutover, retain the current Web image as `offersteady-global-web:rollback-before-homepage-film-20260907`.

Rollback must restore the preceding `current` symlink and recreate only Global Web from the retained image. It must not restart Global Backend, Admin, worker, PostgreSQL, Redis, Companion, or any China production service.
