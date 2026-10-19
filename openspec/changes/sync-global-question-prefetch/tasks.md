## 1. Scope and actual Global baseline

- [x] 1.1 Record the user's Global sync/deploy authorization, the CN prefetch scope, Global isolation constraints and testable acceptance requirements.
- [x] 1.2 Read and freeze actual Global Backend image/container, app/Prompt hashes, routes, effective models/configuration/feature flags, deployment identity and non-target component identities; inspect writable-layer drift.

## 2. Minimal candidate and preservation

- [x] 2.1 Migrate only approved Chat/Realtime prefetch/cache/lifecycle nodes and the scheduler module onto the actual Global source baseline.
- [x] 2.2 Prove all non-target source/Prompt hashes and non-approved target AST nodes, published heartbeat/ACK, routes and Global membership/language/model contracts remain preserved.
- [x] 2.3 Freeze candidate payload, hashes, immutable baseline/rollback and offline probe expectations without exporting private environment or real user data.

## 3. Isolated synthetic verification

- [x] 3.1 Pass bounded concurrency, leading/latest/final, cleanup/reset/shutdown and token/cache commit-race regression scenarios against the actual-source candidate.
- [x] 3.2 Pass identity/material-version/expiry/exact-text cache, non-waiting quick/independent detail and grounding evals with only synthetic materials/providers.
- [x] 3.3 Pass relevant Global ordinary/mock/billing/heartbeat/ACK/language compatibility regressions using dedicated local synthetic databases and Redis.
- [x] 3.4 Compare actual baseline/candidate admitted retrieval/read work, leading/final readiness and quick/detail material references; record measured results and limits without extrapolating production P95.
- [x] 3.5 Independently review the frozen candidate, release/gate/failure recovery protections and actual-image offline probe before production mutation.

## 4. Authorized Global Backend release

- [x] 4.1 Build immutable actual-image candidate/private overlay and prepare verified previous-image rollback; preserve effective Compose/configuration/HostConfig/mounts and all non-target components.
- [x] 4.2 Revalidate current/candidate identities and all protected-work gates immediately before switching; reject active or indeterminate work without changing production records.
- [x] 4.3 Perform only the authorized Global Backend cutover after all prerequisites pass, retaining Global mock enabled false and all existing regional behavior.
- [x] 4.4 Verify health/restarts, runtime source/Prompt/routes, effective config/models/flags, public entrypoints, non-target identities and deidentified short error observation; recover the owned previous image if required and safe.

## 5. Release record and user handoff

- [x] 5.1 Record actual release time, immutable baseline/candidate/container hashes, verification outcomes, any recovery and unmeasured real-load/physical-client acceptance.
- [x] 5.2 Review every capability scenario against evidence, update completed task state, validate Markdown links and run `openspec validate sync-global-question-prefetch --strict`.

Local evidence: [actual-Global-source verification record](../../../docs/releases/global-question-prefetch-local-20261016.1.md). The candidate has 331 passing cases plus 16 answer cases and 16 unittest subtests; release protection has 184 passing synthetic tests. Known broader shared-test/baseline differences and test-only adaptations remain recorded; this is not a whole-repository or production P95 acceptance claim.

Production completed at 2026-10-16 01:04:52.674 Asia/Shanghai: actual-image offline probe, repeated five-group zero-activity gates, Backend-only switch to `b31a810a…`, independent live verification and short deidentified error observation pass. Six other components, full config/models/Prompt and Global mock enabled false remain preserved. No rollback was needed; recovery safety was verified synthetically. See [production release](../../../docs/releases/global-question-prefetch-20261016.1.md) and [all 13 scenario checks](verification.md). Real-load P95 and physical-client acceptance remain unmeasured.
