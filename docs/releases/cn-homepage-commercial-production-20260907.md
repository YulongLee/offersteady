# Domestic homepage production release — 2026-09-07

## Result

Owner explicitly authorized deployment while idle. Web release `cn-home-commercial-20260907.1` deployed at approximately 22:48:40 Asia/Shanghai to https://mianshiwen.cn/.

- Current: `/opt/offersteady/releases/20260907-cn-home-commercial-1`.
- Previous: `/opt/offersteady/releases/20260907-cn-usage-film-partner-nav-1`.
- Rollback image: `compose-web:rollback-before-home-commercial-20260907`, image ID `sha256:51252fec788b0d8aa1cec28c6acab351a00200bf99365015994b100d150dd861`.
- Only Web was recreated. Backend, admin, PostgreSQL, Redis, material worker and both analytics container IDs/start times are identical before/after.
- No international deployment or database mutations.

## Baseline and occupancy evidence

Production App.tsx SHA256 matched the pre-development snapshot: `dd2afa56e64f1fe4d0a4ee20733c63c0fe7c0bb94863e805723f5155dc90ca4e`. index.html also matched (`8aab79b8fb352eb09365cceb3c1aa70c4f3b33e906782ab36aaea62b54d860e4`).

One database row still had live status, last activity 16:04:48 CST, over six hours old. This is idle under the existing admin 20-minute activity rule; it was not ended or modified. The deployment used a more conservative 30-minute window, returning zero active sessions, and required zero desktop transports, queued frames/workers, live answer active/pending work, screenshot streams, realtime/screenshot wait executors and active control work. Both pre-build and immediate pre-switch gates passed. This establishes operational inactivity, not proof that no anonymous visitor had a browser open.

## Scope

Cloned the current production release; overlaid only `apps/web/src/App.tsx`, `apps/web/src/homepage-commercial.css`, `apps/web/index.html` from `/private/tmp/offersteady-cn-release-20260907.DTlvCc`. No synthetic preview or test fixtures were deployed. Existing Docker recipe and environment retained; `--no-deps --no-build --force-recreate web` used for cutover. Previous image retained before build, with automatic rollback on post-cutover command failures.

## Verification

- Development report: [local verification](cn-homepage-commercial-development-20260907.md), 366 tests passed, zero failed. Production Docker typecheck and build passed.
- OpenSpec apply workflow used for `optimize-cn-homepage-commercial-clarity`, with explicit owner-authorized deployment follow-up tasks.
- Public build manifest reports the new version; no-JS GET returns the new Chinese H1, existing title/canonical and homepage body.
- `/login`, `/guide`, `/download` HEAD 200. Both existing video paths HEAD 200 video/mp4.
- Partner config GET succeeded and reports enabled. HEAD returns 405 because that API does not expose HEAD; this is not a GET failure.
- Health and nginx configuration checks passed. A first loopback request during Web replacement saw a connection reset; the retry succeeded. Do not describe this as zero-downtime deployment.
- Public robots.txt and sitemap.xml accessible; existing content retained.
- Fresh production Chrome responsive QA passed at 1440/900/390/320, including expanded optional scenarios, no horizontal overflow. Two native videos remain controls/muted/playsinline/preload metadata, without autoplay.
- Actual displayed prices: ¥29.90, ¥69.90, ¥129.90, ¥219.90, ¥329.90. Partner bottom promotion and top link visible.
- Initial reused browser run failed while waiting for render/config; a clean browser profile fully passed. No production code was changed to bypass this check.
- Screenshots and measurement JSON: `design/previews/cn-home-commercial/production/`.

## Known pre-existing exceptions

- The SEO entry bundle budget remains exceeded (production entry approximately 429 KB vs 410 KB check); the local controlled baseline was approximately 441 KB. No latency/conversion improvement claimed.
- www domain returns 200 rather than canonical-host redirect; canonical still points to the non-www domain. This confirms the documented existing redirect test failure. Routing was not changed in this homepage deployment.
- Build npm audit reported 9 dependency issues (2 moderate, 7 high) and Node engine warnings for Electron-related dependencies. No automatic audit fix, runtime upgrade or dependency changes were made.

## Rollback

When authorized and idle, retag the retained rollback image as `compose-web:latest`, run Web-only compose recreate from the previous release with version `cn-usage-film-partner-nav-20260907.1`, restore `/opt/offersteady/current` to that release, then verify manifest/health and core container identity. No database rollback is needed.

Deployment script preserved locally at `/private/tmp/deploy-cn-home-commercial-20260907.sh` and server `/tmp/deploy-cn-home-commercial-20260907.sh`; deployment core identity evidence at server `/tmp/cn-home-commercial-core-before.txt` and `...-after.txt`.
