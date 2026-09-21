## 1. OpenSpec and configuration

- [x] 1.1 Add server-side web-search settings, timeout, source limits, and disabled-by-default feature flag.
- [x] 1.2 Add the `web_answer` billing rate and migration-safe usage-kind contracts.

## 2. Web-search gateway

- [x] 2.1 Define a provider-neutral web-search port and source record.
- [x] 2.2 Implement the DashScope Responses API `web_search` adapter with bounded timeout and normalized sources.
- [x] 2.3 Add safe query normalization, context minimization, provider errors, and structured telemetry.

## 3. Chat and billing integration

- [x] 3.1 Add `webSearchEnabled` to live-answer requests and web-search metadata to task responses.
- [x] 3.2 Reserve `web_answer` usage before task creation, including the seven-day-or-longer pass rule.
- [x] 3.3 Inject bounded sources into the detailed prompt only; preserve quick-stage latency and local fallback.
- [x] 3.4 Settle or release web reservations across success, cancellation, timeout, provider failure, and retries.
- [x] 3.5 Persist source metadata without raw page bodies and preserve old-client compatibility.

## 4. Web client experience

- [x] 4.1 Add the opt-in web-answer control beside automatic answer controls.
- [x] 4.2 Show non-blocking search/fallback states, 20-point pricing or member entitlement, and collapsible sources.
- [x] 4.3 Keep the control and labels aligned with the selected interview language.

## 5. Verification and release

- [x] 5.1 Add billing unit tests for 20-point reservations, idempotency, short/long passes, settlement, and release.
- [x] 5.2 Add web-search gateway tests with mocked Responses API success, timeout, empty result, and malformed payloads.
- [x] 5.3 Add chat integration tests proving quick-first streaming, detailed-only search, fallback, and source propagation.
- [x] 5.4 Add frontend tests for default-off toggle, status states, sources, and old response compatibility.
- [x] 5.5 Add synthetic `ai/evals/` cases for source grounding, privacy minimization, and language routing.
- [x] 5.6 Run OpenSpec validation, backend/frontend tests, build, and production smoke checks.
- [ ] 5.7 Deploy to CN only after confirming no active interview, with feature flag initially disabled and rollback instructions.
