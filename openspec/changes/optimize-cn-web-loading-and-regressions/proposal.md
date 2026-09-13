## Why

The approved local Chinese homepage candidate exceeds existing JavaScript budgets and carries ten failing regressions. The user approved fixing these high-priority issues locally before review, without deployment.

## What Changes

- Defer the live-interview workspace outside the public-page initial dependency graph; warm it during preparation without changing session, audio, answer or billing behavior.
- Reduce generated JavaScript where safely measurable, preserving the existing 410,000-byte entry and 1,350,000-byte total budgets.
- Align nine stale assertions with previously approved homepage/navigation decisions and explicitly isolate the material-deletion failure test.
- Verify production builds, real lazy-loading boundaries, SEO HTML and responsive local preview. Preserve a scoped before/after artifact.
- Non-goals: deployment, international changes, backend tuning, credential rotation, new SEO pages, payment changes or altered interview algorithms.

## Capabilities

### New Capabilities
- `cn-web-loading-quality`: Local frontend loading isolation and regression quality for the approved Chinese candidate.

### Modified Capabilities

None. Existing business behavior remains authoritative, including the permanent partner navigation approved on 2026-09-07 and refined homepage approved on 2026-09-12.

## Impact

Only the isolated candidate under `artifacts/cn-homepage-layout.82qdGV/candidate/apps/web`, its scoped handoff artifacts, and this OpenSpec change. No root app overwrite, production API writes, real user samples, audio capture or new persistence. Public production price verification remains read-only.

## Subsequent CN release authorization — 2026-09-13

After the local handoff and disclosure of the unresolved total-JS budget, the user explicitly requested “帮我上线到国服吧”. This authorizes publishing the reviewed CN homepage, core-search content and loading patches only. Rebase the 32-file cumulative allowlist onto a fresh production-source snapshot, rebuild with live prices, preserve old assets and a rollback baseline, and use the existing static-file/graceful-reload procedure. Overseas, backend, account data, credentials and payment behavior remain excluded. Task 2.2 stays open and its failed budget result remains visible.
