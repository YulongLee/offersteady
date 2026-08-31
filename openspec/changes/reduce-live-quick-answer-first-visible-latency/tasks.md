## 1. Baseline and regression protection

- [x] 1.1 Add focused tests that count session, material, context, and provider-client operations during one streaming answer startup.
- [x] 1.2 Add regression coverage for billing rejection/idempotency, normalization, English output, programming policy, selected materials, cancellation, and history persistence.

## 2. Backend critical-path optimization

- [x] 2.1 Allow trusted internal chat operations to reuse one validated session snapshot when appending the explicit question and reading the context window.
- [x] 2.2 Remove the redundant session activity save from question persistence while keeping the authoritative pre-answer activity touch.
- [x] 2.3 Add a bounded reusable HTTP client to the Qwen-compatible gateway with safe lifecycle cleanup and unchanged provider behavior.

## 3. First-visible-answer telemetry

- [x] 3.1 Record content-free backend timestamps for answer admission, provider request, first raw token, first visible event, and SSE yield.
- [x] 3.2 Acknowledge the first non-empty answer render from the browser exactly once without blocking the stream.
- [x] 3.3 Add privacy and failure-isolation tests for the new answer timing telemetry.
- [x] 3.4 Persist the content-free server, SSE, browser receive, and browser render fields for `answer-first-render` acknowledgements.
- [x] 3.5 Expose answer-stage latency distributions and regression-test that telemetry remains content-free and non-blocking.

## 4. Verification and release

- [x] 4.1 Run focused backend/web tests, AI evals, typecheck, production builds, and a synthetic pre/post latency benchmark.
- [x] 4.2 Validate this OpenSpec change strictly and document measured results plus rollback controls.
- [x] 4.3 Commit and push scoped changes, deploy only affected services, verify production health/logs/billing, and compare post-deploy timing without interrupting active interviews.
- [ ] 4.4 Run the full regression/build suite and deploy the telemetry correction only when no live interview is active.
