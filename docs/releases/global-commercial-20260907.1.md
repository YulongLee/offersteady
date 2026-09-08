# Global homepage commercial clarity release

Deployed to https://offersteady.com at approximately 21:26 CST on 2026-09-07 following explicit owner approval. Version: `global-commercial-20260907.1`.

## Scope

Published the [homepage commercial-clarity change](../audits/global-homepage-commercial-clarity-20260907.md): concise hero, four benefits, earlier canonical pricing, grouped setup videos, expandable comparison, FAQs and closing Start free action. Support remains contact@oneshowailab.com; pricing, policies, entitlements and payment activation are unchanged.

Eleven selected Global Web source/test/template/script files were overlaid on the preceding release. App.tsx differences were checked against the actual server baseline and restricted to public presentation and metadata. LibraryManager.tsx matched the server baseline. No domestic, backend, admin, dependency, database, prompt or Nginx configuration changes were deployed.

## Verification

- Local preflight: 88 tests passed across 10 files; preceding development copy/typecheck/build/static acceptance passed.
- Source archive SHA256: `2102c56784ddf24f0b8bbec125e14c017c9210c36e3b3d0759f7e978bc479f94`, verified on server before extraction.
- Idle gate before build and immediately before replacement: zero live sessions, desktop transports, queue workers, queued frames, active/pending answer tasks and active screenshot streams.
- Server build passed. Existing >500 kB chunk warning remains; main JS gzip 165.05 kB. No claim of runtime performance uplift.
- Only Web recreated with `--no-deps --no-build`; Backend, Admin, PostgreSQL, Redis and Analytics container IDs/start times matched before and after.
- First immediate startup probe reset; retry and subsequent health/version checks passed. Nginx syntax passed, plus 15 independent public-page loopback checks.
- Public manifest confirms production, en-US, same-origin API `/`, unchanged `true:creem` flags and the new version. Backend remains `global-quick-answer-pilot-20260907.1`.
- Public curl checks passed for home, pricing, terms, privacy, refund-policy, contact, about, security, robots.txt and sitemap.xml. Independent titles, descriptions, canonical, H1/body, operator/support and pricing remain readable without JavaScript.
- Login route and anonymous web state returned 200. No real registration, email send, interview or payment was created for testing.
- Production Chrome checks with cache disabled passed at 1440, 900, 390 and 320 px: no unintended overflow, four benefits, seven FAQs, mouse-operated native disclosures, and both videos muted/inline/metadata-preloaded without autoplay. Initial immediate post-click measurement was transient; waiting for layout settling and rerunning all widths passed, without production code changes.

Production evidence: [mobile hero](../../design/previews/global-home-commercial/production/hero-390.png), [desktop pricing](../../design/previews/global-home-commercial/production/pricing-1440.png), [measurements](../../design/previews/global-home-commercial/production/measurements.json). The production measurements file's `baseline` is the deployed new homepage, not the earlier release.

## Rollback

- Current: `/opt/offersteady-global/releases/20260907-global-commercial-1`.
- Previous: `/opt/offersteady-global/releases/20260907-global-review-1`.
- Saved image: `offersteady-global-web:rollback-before-commercial-20260907`.
- Deployment script: `/tmp/deploy-global-commercial-20260907.sh`.
- Core snapshots: `/tmp/global-commercial-core-before.txt` and `/tmp/global-commercial-core-after.txt`.

If rollback is required, check idle state, retag the saved image as `offersteady-global-web:latest`, recreate only Web using the preceding release's Compose/environment and `GLOBAL_RELEASE_VERSION=global-review-20260907.1`, restore the current symlink and recheck manifest/health/public URLs. Do not rebuild or restart core services or remove volumes. Merchant approval and live payment activation remain separate work.
