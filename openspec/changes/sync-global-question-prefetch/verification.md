# Global question prefetch scenario verification

Completed on 2026-10-16. User authorization covers Global synchronization and deployment; the release updated only Global Backend. [Local verification](../../../docs/releases/global-question-prefetch-local-20261016.1.md) and [production record](../../../docs/releases/global-question-prefetch-20261016.1.md) contain exact hashes, test totals, baseline differences and limits. Artifact names below are local evidence under `artifacts/global-question-prefetch-20261016/`, not clone-available Markdown links.

## Global question prefetch parity

| Spec scenario | Executed evidence and result |
| --- | --- |
| Partial updates burst and final arrives | Scheduler leading/latest/final/quiet/max-wait/key-budget cases and real Chat integration pass against actual Global candidate. `verification/candidate-comparison.json` records 41→2 retrieval calls, bounded workers and final ready while obsolete partial remains blocked. |
| Final text is unchanged or older partial arrives late | `test_same_text_final_promotes_prefetch_without_duplicate_stable_event` and `test_late_partial_or_older_final_cannot_overwrite_final_stable_state` pass; final preparation still receives same-text promotion, late partial cannot overwrite it. |
| Document changes without selection revision change | Real cache tests cover version, readiness/index, activity and collection changes. Synthetic comparison rejects stale v1 without changing binding revision, then uses refreshed v2. |
| Identity, complete text or generation differs | Cross-owner/session, exact normalized full text, same-revision material replacement, duplicate/in-flight, expiry/eviction and late commit tests pass; old partial results do not replace final evidence. |
| Cleanup races an observer or cache commit | Actual-Global adapted cleanup tests preserve all assertion ASTs; queued old generation, admission/clear, cache commit/hit revocation and shutdown pass. Actual reset lock-order test and independent service construction confirm existing Global frame lock is released before stable clear, with no unrelated CN lifecycle migration. |
| User clicks while both workers are slow | Non-waiting cache-miss and real Chat integration tests pass; blocked-prefetch comparison emits visible content while prefetch is still blocked, with one startup session read and original quick fallback; detail uses current material evidence. |
| Regional regression and runtime config inspection | 63 Global behavior cases and 44 dedicated local PostgreSQL/Redis cases pass, including actual original get/generation after 60 minutes without CN deadline API. Offline and live probes preserve Global membership/UTC three-per-day/no wallet, all 74 Prompt files, model/config digest, enabled false, heartbeat/ACK and desktop 1.3.5. |

## Protected release

| Spec scenario | Executed evidence and result |
| --- | --- |
| Mixed development tree contains unrelated regional changes | Runtime inventory/reconstruction match all 235 baseline files; only two approved existing files plus scheduler differ, 233 existing files remain exact. Independent review proves 170 protected methods, six inverse byte edits and whole-file AST outside approved nodes. `production-preflight.json` and live probe confirm image/runtime preservation. |
| Candidate preservation or synthetic check fails | The initial missing-helper candidate failed locally and never reached production; corrected candidate reran successfully. Controller synthetic tests reject payload/source/config/image/mount drift, missing verification and incomplete gates before switch. Final actual-image offline probe passes without network/DB/write/lifespan. |
| Active interview or uncertain gate result | 184 controller/gate tests include first/second gate activity, missing/unknown/invalid metadata, nonzero protected counts despite exit 0 and unavailable gates; no switch occurs. Production preflight and repeated immediate cutover gates show all five required gate groups zero, without data cleanup. |
| Idle verified backend cutover | `production-deploy.jsonl` records only Backend switched to `sha256:b31a810a49f718e360f8ddbcbae0e7aa3d0184012b8993cd0e2f5f973bc7657a` at 2026-10-16 01:04:52.674 Asia/Shanghai. Four Compose/one Env, full configuration/models/HostConfig/mounts and six other component identities remain unchanged; no proxy reload. |
| Candidate fails post-switch verification | Synthetic fault injection verifies owned-image Backend-only recovery, restoration checks, new-activity deferral and refusal to overwrite foreign/later containers or images. Five direct verify tests reject stopped/unhealthy/starting/missing-health/restarted containers. Real production verification passed, so no actual recovery or fault rehearsal was performed; immutable previous image/config remain available. |
| Successful release with no real-user test | Independent production verify and five public HTTP checks pass, protected source/routes/flags unchanged, 135-second short observation healthy/restart 0 with no counted errors and all six non-target identities rechecked. HTTP 5xx counts include access lines and structured status fields; only aggregates are exported. Production record explicitly leaves sustained P95, physical audio and real model quality acceptance unmeasured. |

## Execution totals and limits

Actual-source candidate: **331 passing cases**, plus **16 answer cases** and **16 unittest subtests**. Release-controller/gate protection: **184 passing synthetic tests**. Existing broader shared-test failures are reproduced on the actual old Global baseline and recorded separately; test-specific adapters and assets do not enter the three-file release. Source hashes remain Chat `46d9db27…`, Realtime `d344c608…`, Scheduler `36bc5ab7…`.

Production image probe and live verification cover 162 app files, 74 Prompt files, 151 HTTP paths, two mock WebSockets, 170 protected methods and 19 module files. Effective configuration digest remains `fd56081071dcad5b9a6933d31fab72919c07a88f335fd688117531e5f565338d`. Local testing used only synthetic materials/providers and dedicated loopback PostgreSQL/Redis; production checks used aggregate metadata and anonymous public/read-only routes. No real interview creation, user-content export, actual provider call, physical device acceptance or production rollback rehearsal is claimed.
