## Context

The isolated candidate already has the locally approved homepage and SEO work. Its baseline has 414 tests, 404 passing; entry JS is 452,836 bytes and total JS 1,373,364 bytes. Existing published release notes supersede old assertions about six cards, fabricated marketing metrics and bottom-only partner navigation. They do not authorize new business behavior here.

## Goals / Non-Goals

Goals: reduce actual public startup dependencies, retain strict budgets, restore meaningful deterministic tests, preserve design and SEO, and provide a local candidate with evidence.

Non-goals: production/overseas deployment, backend performance, dependencies or model upgrades, price changes, new landing pages or credential changes.

## Decisions

1. Extract the existing live-page implementation mechanically into a lazy route. Move its context contract into a small shared module; pass shared brand/account UI as slots. Keep session/audio/answer lifecycle bodies unchanged. Do not merely rename a vendor chunk to bypass the entry budget: inspect the transitive initial graph as well.
2. Warm the workspace chunk on preparation mount. Loading modules must not start capture, subscriptions or sessions. Keep the answer renderer independently lazy; prefetch its existing module together with the live route during preparation. Failures from optional warm-up are handled and do not block preparation. Direct visits retain the existing Suspense loading state.
3. Evaluate existing compiler compression and duplicate output without removing Word export, math rendering, billing or login. Any compiler-option change requires measured output savings and verification. Do not raise budgets or blindly remove all dependency side effects.
4. Update the nine obsolete tests to protect the current approved semantics. Explicitly mock the deletion failure rather than call an API or replace the expected network error with a 404.
5. Ordinary route tests may retain the existing eager test alias; add separate tests for the real lazy loader and production dependency graph so that alias cannot hide a broken split.

## Risks / Trade-offs

- First direct live-route navigation needs a chunk fetch → prepare-page warm-up, explicit loading state and actual lazy-boundary tests; no per-answer load added.
- Extracting a large component can change imports/context identity → mechanical move, shared singleton context and full behavioral regressions.
- Shrinking entry bytes does not guarantee improved real-world p95 or ranking → report bytes and local checks only; no unsupported latency/ranking claims.
- Existing unrelated changes in root → only isolated candidate and scoped patch. Preserve before snapshot and no deployment.

## Migration Plan

No production migration. Build and inspect locally; retain the saved pre-change candidate for reversal. A future deployment requires separate authorization and rebasing the scoped patch onto actual production.

## Open Questions

Production field performance and search-console data are not available for this local task. They are not a blocker to deterministic source/build checks.

## Authorized production handoff — 2026-09-13

The later explicit CN deployment request supersedes the original local-only delivery boundary, not the functional non-goals or size thresholds. Build from the current production Web source plus the 32 reviewed files. Back up the live Web document root/config, source and image; retain every old hashed asset; install resources before atomically replacing HTML; validate Nginx and gracefully reload without recreating containers. Verify all 30 sitemap routes under normal and Baiduspider UAs, current catalogue prices, old/new assets and read-only business entry points. Record unrelated pre-existing service faults separately rather than fixing them in this frontend release. Do not assert all gates passed while total JS remains over budget.

## Verification outcome and deferred item

Entry is now 400,328 bytes; the real initial import graph is 468,120 bytes versus 520,634 before (10.09% less). The unmodified total-JS gate still fails at 1,374,135 bytes, 24,135 above its ceiling. Safe Oxc option probes, docx import restructuring and a temporary Terser measurement did not close this gap; none was adopted, and no dependency/config change remains. Task 2.2 remains incomplete, rather than weakening the budget or removing features. The extracted LivePage body was compared byte-for-byte after reversing only its new UI slots/signature; lifecycle logic is identical. Full suite is 418/418, including three real lazy-route tests; no production/real-user latency verification is claimed.
