# Global homepage comparison — September 7, 2026

Deployed at approximately 16:06 CST to https://offersteady.com as `global-comparison-20260907.1`.

## Scope

Approved feature-first comparison with eight capabilities and one grouped pricing row. Three real competitors use partially masked names, with dated evidence and uncertainty disclosures. No lowest-price, performance or exclusivity claims. Evidence is retained in [research note](../global-comparison-research-20260907.md).

Only `apps/web-global/src/App.tsx`, `HomepageAdvantages.tsx` and `styles.css` were overlaid on the verified production baseline. App differs only by import and homepage insertion. CSS includes the comparison and mobile public-navigation wrapping. No backend, admin, payments, database, Companion, AI, or China changes. Local preview/test fixture was not included in the overlay.

## Verification

- 57 tests passed; English audit, production TypeScript/build and strict OpenSpec validation passed locally. Updated header assertion after initial test failed on accessible-name whitespace.
- Separate server production build passed using existing production commerce flags (`true:creem`).
- Before build and before cutover: zero live interviews, desktop transports, audio workers/frames and active/pending answer tasks.
- Production browser confirms all three masked headings, nine body rows, no full competitor names in the section, and both existing videos.
- Desktop 1440px and phone 375px have matching page widths without horizontal overflow. Production screenshots retained under `design/previews/global-advantages/production/`.
- Public build marker is `global-comparison-20260907.1`; health is OK. Nginx validates; post-release Web error count is zero.
- Backend, admin, PostgreSQL, Redis and analytics container IDs/start times unchanged. A cutover startup probe briefly reset before succeeding.

## Rollback

Current: `/opt/offersteady-global/releases/20260907-global-comparison-1`.
Baseline: `/opt/offersteady-global/releases/20260907-global-usage-film-1`.
Saved image: `offersteady-global-web:rollback-before-comparison-20260907`.
Deployment script: `/tmp/deploy-global-comparison-20260907.sh` on the overseas server.

Restore the saved image as `offersteady-global-web:latest`, recreate only Web from the baseline with `--no-deps --no-build`, then restore the current symlink and verify health. Do not recreate core services. Baseline environment file remains unchanged; future rebuilds must explicitly export the desired `GLOBAL_RELEASE_VERSION`.
