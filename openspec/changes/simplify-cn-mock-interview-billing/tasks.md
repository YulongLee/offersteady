## 1. Confirm policy and implementation contract

- [x] 1.1 Record user confirmation for every active member, CN business date, flat charge and start-based deadline.
- [x] 1.2 Audit current billing, lifecycle, Global isolation and relevant specs; establish apply-ready design.

## 2. Backend policy and lifecycle

- [x] 2.1 Implement atomic one-free quota and 100-point-only CN sessions; preserve financial history and exact fault compensation.
- [x] 2.2 Persist first-start deadline and enforce expiry in repository transitions, generation fences and recovery candidates, including legacy started sessions.
- [x] 2.3 Integrate runtime stop/cancel/report, command/heartbeat/reconnect/reaper expiry and expose authoritative timing fields.

## 3. User-facing rules

- [x] 3.1 Update CN mock pricing, confirmation, session duration and expiry presentation without minute-fee prompts.
- [x] 3.2 Refresh quotes at business midnight, visibility recovery and stale-price failures; verify creation retry behavior.

## 4. Verification and handoff

- [x] 4.1 Run synthetic PostgreSQL quota, concurrent creation, midnight, fixed charge, historical refund and deadline regressions.
- [x] 4.2 Run runtime/API, Global isolation and ordinary billing regressions plus relevant Web tests/typecheck/build.
- [x] 4.3 Record executed results and local delivery limitations; run strict OpenSpec and Markdown link checks.

Verification: [local delivery record](../../../docs/releases/cn-mock-flat-billing-local-20261015.1.md). The final Backend regression passed 353 tests; relevant Web tests passed 43 cases, typecheck/build passed. Full Web had 496 passes and 3 pre-existing Nginx contract failures, reproduced against files identical to the starting Git baseline. User subsequently authorized CN Backend/Web deployment on 2026-10-15.

## 5. Authorized CN deployment

- [x] 5.1 Inspect actual Backend/Web baselines and current user-work gates; prepare minimal verified candidates preserving live features and 1.3.5 manifest.
- [x] 5.2 Verify actual-baseline candidate behavior and unchanged environment/model/other-service invariants; retain compatible rollback artifacts.
- [x] 5.3 Idle-gate and switch only CN Backend/Web; verify public health, mock entry/assets, effective pricing policy and existing release manifest.
- [x] 5.4 Record production results, timing and rollback identifiers; validate OpenSpec and delivery links.

Production: [2026-10-15 CN release](../../../docs/releases/cn-mock-flat-billing-20261015.1.md). Actual-baseline Backend candidate passed 275 cases; browser ran 8 synthetic scenarios under live CSP; 71 cutover/gate tests and 30 public checks passed. Only CN Backend/Web switched; live heartbeat/model/configuration, other services and three 1.3.5 downloads retained. The actual baseline required four standard-channel guards to prevent mock minute charging; only those methods were added, preserving 165 other RealtimeSpeechService methods.
