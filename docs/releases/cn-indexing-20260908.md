# Domestic indexing readiness — production 2026-09-08

Version `cn-indexing-20260908.1` published 00:38:12 CST. See [full audit, verification and rollback](../audits/mianshiwen-cn-20260908-indexing/FULL-AUDIT-REPORT.md).

- Source worktree: `/private/tmp/offersteady-cn-release-20260907.DTlvCc`; change `fix-cn-indexing-readiness` (5/5).
- Production source release remains `/opt/offersteady/releases/20260907-cn-home-downloads-1`, modified only by exact source bundle `/tmp/cn-indexing-release-20260908/cn-indexing-sources-20260908.tgz`.
- Durable candidate/latest image: `sha256:ce7db2a183f2f35327255218d026413f2963d4f1e89cb3510d71dd8347879207`.
- Running Web container not recreated: static assets and documents updated before graceful Nginx reload. Eight core container IDs unchanged; backend version unchanged. Caddy, authentication, API, database, interviews and international deployment untouched.
- All current hashed assets plus five recent domestic release images' JS/CSS retained. Old main-DLJpquzR.js restored byte-identically; missing synthetic assets still 404. Standard deploy script now invokes retention before Web switch; bespoke future deploys must invoke `scripts/retain-web-assets.sh` too.
- Public www GET/HEAD routes redirect 308; private/auth/API/promotion routes excluded. HTTP www remains a bounded two-hop path via Caddy HTTPS.
- 30 sitemap URLs retained; homepage lastmod updated only. Existing terms/privacy become own indexable documents without changes to legal text; not bulk new SEO content.
- 380 Web tests, typecheck, build, Nginx, 30-source/32-built/32-production indexability checks passed. Existing test:seo-build JS budgets still fail; no independent lint script configured. No performance percentage or inclusion guarantee.
- Server backup, before/after IDs and rollback function: `/tmp/cn-indexing-release-20260908/`. Previous image `compose-web:baidu-verification-20260908`; restore prior HTML/config/source and image tag, no DB rollback. Newly retained assets need not be deleted on rollback.
- Temporary smoke containers removed after validation. No business data removed.
