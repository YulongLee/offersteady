# Domestic homepage downloads deployed

2026-09-07 23:30:56 CST: `cn-home-downloads-20260907.1` deployed to https://mianshiwen.cn/ after explicit owner authorization.

- Current: `/opt/offersteady/releases/20260907-cn-home-downloads-1`.
- Previous: `/opt/offersteady/releases/20260907-cn-home-commercial-1`.
- Rollback image `compose-web:rollback-before-downloads-20260907`, ID `sha256:d32785e0ff56c382c68b49d3e33c7784f66f230aaaa8d188de969045cd032e8e`.
- Production App baseline checksum `fe6d0eeaba016aa29db383bdda1d9ea694c5e4251171a5b1b05d009dd7b3aa89` checked before applying the three source files documented in [development verification](cn-home-downloads-development-20260907.md). No test/preview fixtures deployed.
- Pre-build and pre-switch gates: zero live sessions active in the preceding 30 minutes; zero desktop transports, queued speech frames/workers, answer active/pending work, screenshot admission, realtime/screenshot waiters and control executor activity. The old live-status row last active at 16:04:48 remained untouched, excluded under existing idle activity rules.
- Only Web recreated with no-deps/no-build. Backend/admin/database/Redis/material worker/analytics container IDs and start times unchanged (server `/tmp/cn-downloads-core-before.txt` and `...-after.txt`). No international changes.
- 372 development tests and local build passed; server typecheck/build also passed. Health/nginx checks successful. First startup probe saw connection reset, retry succeeded; this is not a zero-downtime claim.
- Public manifest confirms new version. Actual Windows and both Mac links point to existing domestic 1.2.15 installers. All three bounded GET Range probes returned 206 and correct EXE/DMG MIME types. HEAD initially returned 405 on the GET-only API; corrected probe method, not application behavior. No full package downloads performed.
- Production browser checks passed at 1440/900/390/320; Mac menu fits viewport, Space opens, Escape closes; prices, partner entry and both videos retained. Screenshots under `design/previews/cn-home-downloads/production/`.
- Existing SEO bundle-budget/redirect exceptions and dependency audit/Node engine warnings remain unchanged in scope. Entry bundle approximately 442 KB. No runtime performance gain claimed.
- OpenSpec apply workflow recorded deployment in `optimize-cn-homepage-commercial-clarity`.

## Rollback

When owner-authorized and idle, retag the retained image as `compose-web:latest`, recreate only Web from the previous release using `cn-home-commercial-20260907.1`, restore `/opt/offersteady/current` to the previous directory and verify manifest/health. No database rollback needed. Script: `/tmp/deploy-cn-downloads-20260907.sh` on server (local `/private/tmp/deploy-cn-downloads-20260907.sh`).
