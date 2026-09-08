# Global usage tutorial — 2026-09-07

Released around 14:00 CST to `https://offersteady.com` as `global-usage-film-20260907.1`.

## Scope

Added an English getting-started tutorial after workflow on the homepage, preserving the product film and pricing. Reused existing responsive player styles. Controls, muted, playsInline and metadata preload; no autoplay. Original 49-second 1920×1080 H.264/AAC file (7,809,405 bytes) retains narration.

Only `apps/web-global/src/App.tsx` and two versioned media assets were overlaid on the production baseline; regression test added locally. China and all core business code unchanged.

## Verification

- 56 tests across 5 Global Web suites passed.
- English-copy audit, production typecheck/build and strict OpenSpec validation passed. The first local build lacked production environment variables and was rerun successfully with them explicitly set.
- Pre-build and pre-cutover gates: zero live sessions in the active Global database, desktop transports, audio workers/frames and active/pending answer tasks.
- Public build marker matches; video returns 200 video/mp4, poster 200 image/jpeg, range returns 206 with 1,024 bytes.
- Deployed MP4 SHA256 matches source: `6a7c4cd444b383ee1d88d70e4920bde0c4abf33b1290ca05554b7a7560193dd2`.
- Health OK; Nginx configuration passes. Backend/Admin/Postgres/Redis/analytics container IDs and start times unchanged. Web error log count was zero after cutover. A startup probe briefly reset before succeeding.
- Real-browser visual acceptance remains with the user; automated UI player assertions passed.

## Release and rollback

Current release: `/opt/offersteady-global/releases/20260907-global-usage-film-1`.
Baseline: `/opt/offersteady-global/releases/20260907-global-homepage-pricing-1`.
Rollback image: `offersteady-global-web:rollback-before-usage-film-20260907`.
Deploy script: `/private/tmp/deploy-global-usage-20260907.sh`.

Only Web was rebuilt/recreated with `GLOBAL_RELEASE_VERSION=global-usage-film-20260907.1` exported for Compose. The baseline environment file was preserved to avoid changing backend release configuration. Any future rebuild must explicitly set the desired release version. Rollback restores the saved Web image and prior current symlink, without restarting core services.
