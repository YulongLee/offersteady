## Why

The current Global homepage downloads the interview application before displaying its interactive public content, then waits for `/api/v1/web/state`. Read-only measurements on 2026-09-29 found slow public resource transfer (a roughly 185 KiB compressed entry took 5–19 seconds locally), despite low server load and 134–186 ms state processing. Eager below-the-fold video assets add unnecessary startup traffic.

## What Changes

- Separate the public/auth entry from the protected workspace bundle. Public pages render without loading business state; login renders before any optional session restoration completes.
- Preserve the current English design, public metadata, public downloads, authentication checks, and every workspace feature.
- Defer below-the-fold video posters until near the viewport and video sources until playback is requested, including the initial static HTML.
- Add regression tests and production-build/browser checks for request isolation, auth handoff, routes, media loading, and entry size.
- Initially implement and verify locally. Following the user's explicit deployment request on 2026-09-29, publish only the verified Global Web build after checking that no interview is active. CDN, DNS, backend, desktop, pricing, and model changes remain excluded.

## Capabilities

### New Capabilities

- `global-lightweight-web-entry`: Independent public/auth loading, lazy protected workspace, and demand-loaded promotional media.

### Modified Capabilities

None. Existing workspace, commerce, language, and app-entry-shell requirements remain intact.

## Impact

Only `apps/web-global` source, static-page generation, tests, and related release documentation. No new runtime dependency or personal-data storage. Synthetic accounts and intercepted APIs are used for local tests; no production interview, payment, or provider call is made. The source baseline is the released `20260929-global-practice-1` candidate; unrelated dirty workspace changes are preserved.

The authorized deployment additionally includes scoped Web-only release scripts, exact runtime preservation, old hashed assets, a rollback Web image, and read-only post-deployment checks. No other production container is restarted.
