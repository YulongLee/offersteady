## 1. Configuration and routing

- [x] 1.1 Add an optional server-only quick-answer model setting with fallback to the shared chat model.
- [x] 1.2 Route quick generation, repair, continuation, provider payloads, results, and safe telemetry through the resolved quick model while preserving detail-stage routing.
- [x] 1.3 Reinforce the existing normalized-question protocol at the final quick instruction boundary without changing detail prompts.
- [x] 1.4 Add an optional server-only detailed-answer model setting with fallback to the shared chat model.
- [x] 1.5 Route detailed generation, language repair, continuation, provider payloads, results, task provenance, and safe telemetry through the resolved detail model.

## 2. Verification coverage

- [x] 2.1 Add backend regression tests for dedicated routing, fallback routing, continuation routing, and actual model telemetry.
- [x] 2.2 Add a synthetic AI evaluation case for quick-model normalization, grounding, language, completeness, and quick/detail consistency.
- [x] 2.3 Add a real-provider quick-model probe that uses synthetic data and reports privacy-safe compatibility and latency results.
- [x] 2.4 Extend routing regressions and synthetic AI evaluations to cover the dedicated detail model and quick/detail continuity.
- [x] 2.5 Add a real-provider detailed-answer probe using synthetic quick anchors and retrieval evidence.

## 3. Documentation and validation

- [x] 3.1 Document the new environment variable, candidate model, isolation boundary, and rollback behavior.
- [x] 3.2 Run focused backend tests, AI eval checks, the authenticated provider probe, and strict OpenSpec validation; record measured results without deploying production.
- [x] 3.3 Document the detailed-answer model override and run focused tests, both authenticated provider probes, compilation, and strict OpenSpec validation without deploying production.
