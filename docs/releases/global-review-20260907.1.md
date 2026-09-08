# Global merchant-review remediation release

Deployed to https://offersteady.com at approximately 20:48 CST on September 7, 2026, following explicit user approval after local acceptance.

## Scope

Published the approved public-site remediation described in the [development audit](../audits/global-merchant-review-remediation-20260907.md). Support remains contact@oneshowailab.com. Actual prices and product entitlements are unchanged; live payment acceptance was not enabled.

Thirteen Web source/test/template/script files were overlaid onto the current server release. App.tsx and styles.css diffs were checked against the server baseline and contain only public presentation/metadata changes. LibraryManager.tsx is unchanged, with SHA256 `81f9ada346cdaf912c3e48216acd7de5493c72b007b258e1ca95ace3fe9e08e0`. No domestic files, backend, administration, dependencies, database schemas, AI prompts or Nginx configurations were deployed.

## Gates and verification

- Before building and immediately before replacing Web: zero live interviews, desktop transports, queue workers, queued frames, active/pending live-answer tasks and active screenshot streams.
- Rollback image saved before changes. Source archive hash verified on server: `3e8e1e31a20f202dd1698a745ccf2642b2a01838bda11153c9dba07958d63b3c`.
- Server production build passed with existing dependency cache. Existing large-main-chunk warning remains; main JS gzip is 164.60kB. Prior local acceptance passed 83 tests, typecheck, English copy audit and static merchant checks.
- Recreated **only Web**, with `--no-deps --no-build`. Backend, Admin, PostgreSQL, Redis and Analytics container IDs and start times matched exactly before/after.
- Initial startup probe encountered a connection reset; retry and subsequent health/version checks passed. This was not treated as an immediate successful probe.
- Nginx syntax check passed; all 15 public route documents passed server-loopback checks.
- Public build manifest: `global-review-20260907.1`, production, en-US, same-origin API `/`, existing `true:creem` flags unchanged. Backend remains `global-quick-answer-pilot-20260907.1`.
- Creem readiness remains Test mode, ready=false, blocker `product_mappings_missing`; no live payment setup or test charge was performed.
- Public curl run without `--baseline` passed Home, Pricing, Terms, Privacy, Refund Policy, Contact, About, Security, robots.txt and sitemap.xml: all HTTP 200.
- Seven independent public pages expose their own title, description, canonical, H1, body and operator/email without JavaScript. Pricing exposes current prices, billing and access timing. Old launch/payment phrases were absent in all checked page outputs.
- Public browser checks with cache disabled passed homepage and Pricing at 1440, 390 and 320px; no page overflow, visible operator, no old payment text, four disabled paid controls on Pricing.
- `/login` and `/api/v1/web/state` returned 200 via loopback. No real account registration, email sending, paid transaction or live interview was created as a smoke test.

Production screenshots: [Home mobile](../../design/previews/global-review-remediation/production/home-390.png), [Pricing desktop](../../design/previews/global-review-remediation/production/pricing-1440.png), [Pricing mobile](../../design/previews/global-review-remediation/production/pricing-390.png).

## Baseline and rollback

- Current release: `/opt/offersteady-global/releases/20260907-global-review-1`.
- Previous release: `/opt/offersteady-global/releases/20260907-global-feedback-1`.
- Rollback image: `offersteady-global-web:rollback-before-review-20260907`.
- Rollback image ID: `sha256:d42fd44d7abe5161e175d0e3e468c1e4cda6e4bbe6287d2ec8350743bae47dc2`.
- Release script: `/tmp/deploy-global-review-20260907.sh`.
- Build files: `/tmp/web-global-review.Dockerfile`, `/tmp/global-review-build-override.yml`.
- Core identity snapshots: `/tmp/global-review-core-before.txt`, `/tmp/global-review-core-after.txt`.

If rollback is needed, check idle state, tag the saved image as `offersteady-global-web:latest`, recreate only Web with the preceding release's Compose/environment and `GLOBAL_RELEASE_VERSION=global-feedback-20260907.1`, restore the current symlink to the preceding release, and recheck manifest/health/public URLs. Do not rebuild or restart core services, remove volumes, or touch domestic infrastructure.

Merchant approval remains a separate provider decision. Website deployment does not guarantee approval or replace operator/legal review of the published policies.
