## 1. State request coordinator

- [x] 1.1 Add authentication-scoped in-flight and short-TTL state caches to `BackendPreviewInterviewAdapter` without caching failures.
- [x] 1.2 Add `force` state-refresh options and return independent state values while preserving abort and request headers.

## 2. Freshness boundaries and regressions

- [x] 2.1 Update mutation, billing, library-processing and session-transition refresh callers that require authoritative state to use forced refreshes.
- [x] 2.2 Add adapter regressions for concurrent merging, public/authenticated isolation, TTL reuse, expiry, failure retry, forced refresh and cache replacement.

## 3. Verification

- [x] 3.1 Run focused Web adapter and application initialization tests plus Web typecheck.
- [x] 3.2 Run the relevant Web production build and strict OpenSpec validation; record that no production deployment was performed.

## Verification notes (2026-10-13)

- Passed: adapter and application initialization tests (47 tests), Web typecheck, production Web build, `openspec validate dedupe-web-state-refreshes --strict`, and `git diff --check`.
- Full Web suite: 489 passed, 3 existing Nginx release-contract assertions failed because the current configuration does not contain the older `map`/legal-route/partner-program patterns. No new failure was introduced by this change.
- No production deployment was performed. The change is ready for a later idle-window Web rollout and post-deploy P95/request-count comparison.
