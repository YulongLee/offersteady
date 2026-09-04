# Verification

Verified on 2026-09-05 before the domestic production release gate.

- Desktop full suite: 184 passed across 33 files.
- Desktop typecheck and production build: passed for 1.2.14.
- Backend full suite: 499 passed and 20 skipped.
- Two timing tests that fluctuated once under local load passed three focused reruns and the second full run.
- Strict OpenSpec validation and `git diff --check`: passed.

## Production rollout

- Final gate: zero realtime-active interviews in the preceding 10 minutes and zero session activity in the preceding 2 minutes.
- Rollback Backend image: `offersteady-backend:rollback-b8b7972-pre-1.2.14`.
- Domestic Backend manifest/source commit deployed: `b8b7972ab5b6a31f7301c402b400a8677af37b6b`.
- Only the Backend container was recreated; Web, Admin, PostgreSQL, Redis, Analytics and Promotion Analytics retained their container identities.
- Public `/healthz`, `/app`, `/api/v1/web/state`, `/offersteady-build.json` and apex health returned HTTP 200.
- Public release state reported macOS arm64, macOS x64 and Windows x64 at 1.2.14.
- All three download routes returned HTTP 206 for a one-byte range request.
- First five-minute privacy-safe sample: 1,227 ordinary requests, 245.4 requests/minute, P50 3.62 ms, P95 18.41 ms, P99 70.49 ms, max 607.04 ms and zero observed server errors.
- Existing older Companions keep their previous lifecycle until users upgrade; the single-instance and terminal screenshot-suspension benefit is realized by 1.2.14 clients.
