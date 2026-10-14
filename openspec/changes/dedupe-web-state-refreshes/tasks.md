## 1. State request coordinator

- [x] 1.1 Add authentication-scoped in-flight and short-TTL state caches to `BackendPreviewInterviewAdapter` without caching failures.
- [x] 1.2 Add `force` state-refresh options and return independent state values while preserving abort and request headers.

## 2. Freshness boundaries and regressions

- [x] 2.1 Update mutation, billing, library-processing and session-transition refresh callers that require authoritative state to use forced refreshes.
- [x] 2.2 Add adapter regressions for concurrent merging, public/authenticated isolation, TTL reuse, expiry, failure retry, forced refresh and cache replacement.

## 3. Verification

- [x] 3.1 Run focused Web adapter and application initialization tests plus Web typecheck.
- [x] 3.2 Run the relevant Web production build and strict OpenSpec validation; record verification and deployment evidence.

## Verification notes (2026-10-14)

- Current deployment status: withdrawn at 22:36 Asia/Shanghai. The candidate used stale pre-mock-interview Web source and omitted the deployed mock routes. Web was restored to the retained `pricing-copy-hourly-20261011.1` image; Backend/DB/Redis were unchanged. Local implementation remains verified, but production readiness requires rebuilding from the actual running component and checking preserved routes/features.

- Passed: adapter and application initialization tests (48 tests), Web typecheck, production Web build, `openspec validate dedupe-web-state-refreshes --strict`, and `git diff --check`.
- Full Web suite: 490 passed, 3 existing Nginx release-contract assertions failed because the current configuration does not contain the older `map`/legal-route/partner-program patterns. No new failure was introduced by this change.
- Deployed to CN Web during an idle window at 2026-10-14 00:34 Asia/Shanghai. The release copied `/opt/offersteady/releases/20260923-cn-quick-stage-1`, overlaid only the approved Web state-refresh files, and switched `current` to `/opt/offersteady/releases/20261014-cn-web-state-dedupe-1`.
- Both pre-cutover idle gates reported zero live interviews, live-page leases, recent audio tracks, and unfinished answers. Only `compose-web-1` was recreated; the previous image is retained as `compose-web:rollback-before-web-state-dedupe-20261014-1`.
- Post-deploy `/`, `/login`, `/healthz`, `/api/v1/web/state`, and `/offersteady-build.json` checks returned 200; the public build manifest is `web-state-dedupe-20261014.1`, the Web restart count is 0, and recent Web logs contain no error-level entries. Production P95 improvement still requires observing the user's real test window.
