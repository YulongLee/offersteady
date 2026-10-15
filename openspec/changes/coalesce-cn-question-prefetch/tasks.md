## 1. Scope and baseline

- [x] 1.1 Confirm first-round CN prefetch/cache scope and local-only delivery; document actual running source baseline and protected behavior.

## 2. Implementation

- [x] 2.1 Implement bounded leading/latest/final-priority scheduling, token invalidation and cleanup without changing the existing cold/audio/subtitle path.
- [x] 2.2 Integrate monotonic stable partial/final observation and preserve final notifications even when stable text is unchanged.
- [x] 2.3 Bind prepared results to owner/current materials/exact question, reject duplicate/stale/expired generations and preserve the one-snapshot non-waiting click path.

## 3. Verification

- [x] 3.1 Reproduce old over-submission/cache defects with synthetic regressions; pass concurrency/final/cleanup/identity/material-version/expiry tests.
- [x] 3.2 Add and execute synthetic AI evidence-selection eval cases for partial/final, current materials and safe quick fallback; preserve Prompt/model behavior.
- [x] 3.3 Run relevant ordinary/automatic/Global/mock/billing/subtitle/lifecycle regressions using only isolated synthetic databases/providers.
- [x] 3.4 Build a local actual-CN-source candidate by approved-node overlay and prove unrelated code/Prompt/routes and existing performance patches remain unchanged.
- [x] 3.5 Run reproducible baseline/candidate synthetic comparisons for admitted work, read counts, leading/final readiness, explicit quick startup and material reference correctness.

## 4. Local handoff

- [x] 4.1 Independently review implementation and fix any remaining correctness/resource/race issues.
- [x] 4.2 Record exact tests, measured limits, scenario coverage and remaining user acceptance; validate OpenSpec, links and diff; leave production untouched for the user's later release decision.

Evidence: [scenario verification](verification.md) and [local delivery record](../../../docs/releases/cn-question-prefetch-local-20261015.1.md). Relevant final tests pass; two unrelated broad-suite failures also reproduce on the saved actual CN baseline and remain explicitly recorded. This completed phase was local only; the user explicitly authorized production deployment afterwards on 2026-10-15.

## 5. Authorized CN release

- [x] 5.1 Re-read actual CN runtime images, source inventory and deployment identity; reject drift and record authorization.
- [x] 5.2 Reverify frozen candidate, prepare backend-only image/private overlay and rollback with unchanged models/config/other components.
- [x] 5.3 Verify all protected-work gates immediately before a minimal CN Backend cutover.
- [x] 5.4 Verify health, runtime source, routes/Prompt, models/environment and unrelated component identities; rollback on failure.
- [x] 5.5 Record actual production results, baseline/candidate identifiers, validation limits and user test entry; validate OpenSpec and links.

Authorized release result: [production record](../../../docs/releases/cn-question-prefetch-20261015.1.md), CN Backend `cc040a55…` healthy, all release/source/config checks passed, other seven containers unchanged. No production rollback was needed; real-traffic P95/user acceptance remains unmeasured.
