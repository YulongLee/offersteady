# Simplified homepage downloads — September 7, 2026

Deployed Global Web at approximately 17:06 CST as `global-downloads-simple-20260907.1`.

Removed download heading, helper notes, installation disclosure, Mac version/OS descriptions and hero trust-list. Windows remains a direct link; macOS retains Apple Silicon and Intel choices. Existing installer URLs and core behavior unchanged. Static homepage helper text also removed.

59 tests, English audit, local/server production build and OpenSpec validation passed. Mobile/desktop previews have no page overflow. Production browser checks require three Global download links and absence of removed helper copy/trust-list. Build retains the existing >500 kB chunk warning. Deployment gates found zero live sessions/workloads; only Web recreated and core container identities/start times unchanged. Health and Nginx checks passed after one startup probe reset.

Current: `/opt/offersteady-global/releases/20260907-global-downloads-simple-1`.
Baseline: `/opt/offersteady-global/releases/20260907-global-homepage-downloads-1`.
Rollback image: `offersteady-global-web:rollback-before-simple-20260907`.
Server deployment script: `/tmp/deploy-global-simple-20260907.sh`.
Restore saved image as latest, recreate Web only from baseline with no-deps/no-build, restore current symlink and check health. Never recreate core services or delete volumes.
