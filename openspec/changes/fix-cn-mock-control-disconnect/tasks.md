## 1. Baseline and regression

- [x] 1.1 Record user authorization and narrow CN control-close scope; confirm monitored actual module and immutable baseline.
- [x] 1.2 Freshly observe actual CN runtime/contracts and preserve server-only private inputs; reproduce the final-close disconnect regression locally.

## 2. Implementation and local acceptance

- [x] 2.1 Apply only the final-close exception fix; verify cancellation, error visibility, detach ordering and replacement ownership with synthetic tests.
- [x] 2.2 Run existing mock API/audio/runtime/billing/deadline/isolation regressions against the actual candidate and review the complete one-file delta.

## 3. Production preparation

- [x] 3.1 Freeze new single-file controller, full238-input candidate and original1724 rollback; test seven work gates, entity/TCP/ownership and recovery protections.
- [x] 3.2 Build from actual fixed image and run isolated actual-image regressions plus full Schema/settings/dependency/auxiliary/companion probes.

## 4. Authorized CN release and handoff

- [x] 4.1 Wait for natural idle and repeat every work/ownership/TCP gate before switching only CN Backend; stop for any drift or unknown state.
- [x] 4.2 Independently verify actual source/image/configuration/non-targets and collect bounded startup and later error/performance evidence.
- [x] 4.3 Update actual CN baseline, release record and task evidence; run strict OpenSpec validation and hand off for user testing without Git publication.

Published 2026-11-07 02:07:19 Beijing as [cn-mock-control-20261107.1](../../../docs/releases/cn-mock-control-20261107.1.md). Actual58d3/fe11, 238 inputs/237 preserved, full203 Schema/344 settings/44 dependencies, companion1.3.6/d7, Web366 and seven non-targets verified. 271 CN mock tests passed (one pre-existing Global-only case explicitly deselected), 307 release tests plus110 subtests passed, actual-image control-close/cancellation probe passed. Startup16 proxy502 within3.777s recovered; no post-verification5xx. Natural140.848s/157requests/P95 58.54ms; no active-interview peak comparison or real model/test interview created. No Git publication.
