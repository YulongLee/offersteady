## 1. Implementation

- [x] 1.1 Add five-field heartbeat projection to protocol, memory and PostgreSQL repositories.
- [x] 1.2 Add authorized heartbeat idle calculation sharing existing time boundaries; remove duplicate/material-aware reads only from web heartbeat.

## 2. Verification

- [x] 2.1 Add regression tests for read counts, ownership, deletion, idle/ended paths, leases and material-aware operations.
- [x] 2.2 Run isolated PostgreSQL projection tests and identical-load synthetic performance comparison; run relevant existing lifecycle/API/billing/answer/mock regressions.
- [x] 2.3 Validate OpenSpec and fixed-scope deployment overlay guards.

## 3. CN release

- [x] 3.1 Prepare actual-running-image overlay and run isolated candidate verification without touching live service.
- [x] 3.2 Repeat protected-work gates; only when idle, switch backend, verify health/models/configuration/non-target isolation and preserve rollback.
- [x] 3.3 Record measured evidence, deployment status, scenario mapping and user acceptance boundary.

Verification and release evidence: [CN release report](../../../docs/releases/cn-web-heartbeat-lightweight-20261010.1.md). Real-user end-to-end acceptance remains with the user after deployment; two pre-existing assertion failures and one timing exclusion are explicitly recorded in that report.

## 4. Restore the overwritten CN heartbeat (2026-10-14)

- [x] 4.1 Extract the actual running Backend source, restore only the heartbeat method in an isolated candidate, and prove unrelated AST nodes unchanged.
- [x] 4.2 Add restoration regression/release guards and run local synthetic lifecycle, mock, billing and heartbeat checks against the actual-source candidate.
- [x] 4.3 Record local verification, validate OpenSpec, commit and push the approved patch/tests/release tooling to Git.
- [x] 4.4 Build and verify the candidate image, repeat protected-work idle gates, deploy only Backend, and verify effective source, health, mock capability, unchanged components/configuration and rollback evidence.

Restoration evidence: [2026-10-15 CN release](../../../docs/releases/cn-web-heartbeat-restore-20261015.1.md). Code/tooling pushed as `48fcabc` before cutover; only Backend switched at 00:13:19 Asia/Shanghai. Actual-source candidate: 196 passed, four proved baseline failures deselected; release guards: 37 passed; isolated image probe: 18 passed. Real-user acceptance and same-load production P95 remain pending with the user.
