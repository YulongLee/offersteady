## 1. Baseline

- [x] 1.1 Preserve the isolated candidate baseline and classify all ten failing tests against approved release decisions.

## 2. Implementation

- [x] 2.1 Isolate and warm the live route while preserving lifecycle behavior and shared context.
- [ ] 2.2 Reduce generated JS safely and retain original bundle budgets.
- [x] 2.3 Update obsolete tests and isolate the material-deletion failure request.
- [x] 2.4 Add real lazy-loading and production dependency-graph regressions.

## 3. Verification and handoff

- [x] 3.1 Run typecheck, full tests, production build, unchanged budget gate and existing SEO/pricing/indexing checks.
- [x] 3.2 Inspect desktop/mobile local preview and production assets/HTML.
- [x] 3.3 Preserve the scoped patch and document measured results and limitations; validate OpenSpec strictly.

Task 2.2 remains open: total JS 1,374,135 bytes exceeds 1,350,000. The separate entry ceiling now passes. No compiler experiment, dependency change, threshold relaxation or business removal was retained. See the local handoff report at `docs/releases/cn-web-loading-local-20260913.md`.

## 4. Subsequently authorized CN release (2026-09-13)

- [x] 4.1 Rebase the cumulative 32-file allowlist onto actual production Web source and rebuild with live pricing; rerun checks without changing budgets.
- [x] 4.2 Save the production Web baseline and install only reviewed static assets/config/source with old assets retained and no container recreation.
- [x] 4.3 Verify production HTML, sitemap, prices, assets and read-only business entry points; document final version, rollback and pre-existing unrelated faults.

Release `cn-homepage-seo-loading-20260913.1`: 418/418 tests and production HTTP verification passed. Actual release total JS is 1,374,155 bytes (version string adds 20 bytes versus the local build); the unchanged budget gate still fails by 24,155 bytes. Task 2.2 remains open. Four already-approved SEO HTML files received only a version query on their shared stylesheet for cache consistency. See `docs/releases/cn-homepage-seo-loading-production-20260913.md`.
