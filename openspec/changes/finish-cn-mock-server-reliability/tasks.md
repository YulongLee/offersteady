## 1. Scope and baseline

- [x] 1.1 Record authorization, current runtime evidence and server-only scope while preserving the prior webpage fixes and all unrelated local changes.
- [x] 1.2 Specify timing, cancellation, replacement, privacy and edition invariants and validate apply readiness.

## 2. Runtime and cleanup

- [x] 2.1 Make CN valid submissions advance after capture fencing without waiting for native close; retain bounded actual-work tracking, stop/deadline and Global behavior.
- [x] 2.2 Make disconnected microphone final close idempotent and add real-route/replacement/cancellation regressions.

## 3. Safe diagnostics

- [x] 3.1 Add CN allowlisted stage/error/duration diagnostics with task-local random trace, privacy filtering and safe logging failure behavior.
- [x] 3.2 Instrument generation/jobs/cleanup without changing provider calls, prompts, output rules, retries, fault counts or billing; run synthetic failure/privacy regressions.

## 4. Combined local acceptance

- [x] 4.1 Run isolated-PG mock round/API/permission/billing/deadline/isolation and complete CN Web checks, preserving previously tested fixes.
- [x] 4.2 Independently review ownership, cancellation, privacy, CN/Global isolation and scope; validate OpenSpec and documentation links.
- [x] 4.3 Freeze the combined source inventory and local handoff with exact executed results, limits and deployment prerequisites; do not deploy or commit/push Git.

Executed results and release prerequisites: [local handoff](../../../docs/releases/cn-mock-server-local-20261031.1.md).

## 5. Authorized CN production release — 2026-11-01

- [x] 5.1 Freshly verify actual Backend/Web inventories, effective configuration, complete API schema, non-target signatures and user-work gates; freeze release-only inputs.
- [x] 5.2 Build fixed minimal Backend/Web and compatible rollback images; verify actual image probes, compiled Web behavior, unchanged features and independent release review.
- [x] 5.3 Run all repeated idle/ownership/configuration gates and switch only CN Backend/Web; retain fixed rollback and never terminate or bypass protected work.
- [x] 5.4 Independently verify deployed ownership, complete inventories/schema/configuration, public routes/assets and short redacted error aggregates; update production baseline and release record without Git operations.

Released and independently verified: [cn-mock-20261101.1](../../../docs/releases/cn-mock-20261101.1.md). Only CN Backend/Web; all protected-work gates passed, no real user ended, companion/Global unchanged, no Git operations.
