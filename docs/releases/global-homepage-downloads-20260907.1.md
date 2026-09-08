# Global homepage downloads — September 7, 2026

Released at approximately 16:24 CST to https://offersteady.com with Web version `global-homepage-downloads-20260907.1`.

## Scope

Homepage buttons below primary actions: Windows direct download; native macOS selector for Apple Silicon and Intel. Published Global 1.2.17 installers reused, not rebuilt. Free download/account-required notice, mobile desktop-only text and accurate unsigned Windows notice included.

Build generates minimal public metadata and initial HTML links from `apps/backend/app/global_desktop_release_manifest.json`; Web Dockerfile copies only that manifest as build input. No homepage runtime API call or private object key/signed URL in generated data. Existing backend endpoint remains authoritative for access and withdrawal. Updating homepage release metadata requires rebuilding Web after manifest publication.

Only scoped Web sources, index, generation scripts and Web Dockerfile overlaid on the existing release. No backend, admin, authentication, payment, Companion code or China changes.

## Verification

- 59 tests passed. Initial two added test failures were caused by Vite's non-file import.meta.url; filesystem checks were corrected and full suite rerun.
- English audit, production TypeScript/build and strict OpenSpec validation passed; generator idempotence passed.
- Build warns that main JS exceeds 500 kB minified (approximately 156 kB gzip); no dependencies added.
- Local and server Global manifests have identical SHA256. Three public download endpoints returned 307; Global storage URLs returned 206 and 1,024 bytes for range probes. No full installer downloads or installation tests performed in this change.
- Pre-build and pre-cutover gates: zero live sessions and no active desktop/audio/answer workloads.
- Public build marker/health pass. Initial HTML contains all three Global installer links. Production browser confirms expected controls and links at 1440px/375px with no horizontal overflow; screenshots in `design/previews/global-downloads/production/`.
- Nginx config passes. Backend/admin/Postgres/Redis/analytics IDs and start times unchanged. Post-cutover Web error log count zero. One startup probe reset before succeeding.

## Rollback

Current release: `/opt/offersteady-global/releases/20260907-global-homepage-downloads-1`.
Baseline: `/opt/offersteady-global/releases/20260907-global-comparison-1`.
Saved Web image: `offersteady-global-web:rollback-before-downloads-20260907`.
Server deployment script: `/tmp/deploy-global-downloads-20260907.sh`.

Retag saved image to `offersteady-global-web:latest`, recreate only Web from baseline using `--no-deps --no-build`, restore current symlink and verify health. Environment is preserved; future rebuilds must explicitly export desired GLOBAL_RELEASE_VERSION. Never recreate core services or remove volumes for this rollback.
