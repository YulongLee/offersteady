# Global material English copy — September 7, 2026

Deployed at approximately 17:41 CST as `global-material-english-20260907.1`.

## Scope and cause

Production dynamically interpolated Chinese tab names into English empty-state text; the local English correction had not been included in prior homepage-only overlays. Replaced Resume/JD empty states with explicit English and made their add-material dialogs explicitly English. Preserved user-authored text and all upload, parsing, billing and interview behavior.

The production source overlay contains only `apps/web-global/src/LibraryManager.tsx`, SHA256 `81f9ada346cdaf912c3e48216acd7de5493c72b007b258e1ca95ace3fe9e08e0`. Other workspace changes were not deployed.

## Verification

- Global Web: 59 tests across 7 files passed, including synthetic Resume/JD empty-state and dialog regressions.
- English copy audit (648 entries), TypeScript/production build and strict OpenSpec validation passed.
- Server build passed; existing main-chunk size warning remains.
- Public build manifest confirms the new version. Public `LibraryManager-Dg05I4Yw.js` contains `No resumes yet`, `No job descriptions yet`, `Add Job Description`, `Select resume file`, and `Job description text`.
- Deployment gate found zero live sessions and active workloads. Only Web recreated. Backend/admin/database/Redis/analytics container identities and start times unchanged; health and Nginx checks passed. One initial startup probe reset before successful retry.
- No authenticated production upload or real-user-data test was performed.

## Build and rollback

Fresh dependency installs failed with network ECONNRESET. Final build reused the previous successful dependency layer with a temporary Dockerfile setting the new version only for the Web build command. No application dependency or production environment configuration was changed. Temporary server build files: `/tmp/web-global-material.Dockerfile` and `/tmp/global-material-build-override.yml`. The unused legacy build container was stopped.

Current: `/opt/offersteady-global/releases/20260907-global-material-english-1`.
Baseline: `/opt/offersteady-global/releases/20260907-global-downloads-simple-1`.
Rollback image: `offersteady-global-web:rollback-before-material-english-20260907`.
Cutover script: `/tmp/finish-global-material-20260907.sh`.

To roll back, retag the saved rollback image as `offersteady-global-web:latest`, recreate Web only from baseline using `--no-deps --no-build`, restore the current symlink and verify health/version. Do not recreate core services or delete volumes.
