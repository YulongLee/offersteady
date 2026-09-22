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
- [x] 5.7 Deploy to CN only after confirming no active interview, with feature flag initially disabled and rollback instructions.

## 6. Web-mode switching regression fix

- [x] 6.1 Give each intentional manual answer attempt a mode-aware unique request ID, retaining in-flight duplicate protection.
- [x] 6.2 On disabling web mode, cancel only the in-flight web answer, preserve visible text, unlock quick answer, and ignore obsolete stream/realtime updates.
- [x] 6.3 Preserve backend cancellation across a delayed search result and release reservations when a stream disconnects.
- [x] 6.4 Test completed, failed, cancelled, pending, and late-result web-to-local transitions, plus ordinary answers and billing; validate and build locally without deployment. See [verification.md](verification.md).

## 7. CN switching-fix release (authorized 2026-09-23)

- [x] 7.1 Reconcile the seven runtime-file changes against the current CN release and verify the release candidate without unrelated workspace changes.
- [x] 7.2 Retain rollback images and release directory, confirm no live interviews, and switch only Backend and Web.
- [x] 7.3 Verify public endpoints, deployed artifacts, container health, and post-release errors; record release and rollback details. See [CN release record](../../../docs/releases/cn-web-mode-switching-fix-20260923.1.md).

## 8. Explicit non-thinking web answers (authorized 2026-09-23; local only)

- [x] 8.1 Send `reasoning.effort=none` on web-search Responses requests without changing ordinary answer requests, models, timeouts, or billing.
- [x] 8.2 Add request-payload regression coverage and a synthetic AI evaluation case for non-thinking web answers and unchanged failure fallback.
- [x] 8.3 Run focused backend regressions and strict OpenSpec validation; record local results without deploying or changing production configuration. See [non-thinking-verification.md](non-thinking-verification.md).

## 9. CN non-thinking release (authorized 2026-09-23)

- [x] 9.1 Reconcile the gateway-only change with the current CN image and verify the isolated candidate; retain rollback artifacts.
- [x] 9.2 Confirm no live interviews, live page leases, active audio or answer tasks immediately before switching only the backend.
- [x] 9.3 Verify health, public endpoints, deployed request parameters, and a synthetic web search; record the release and rollback path. See [CN non-thinking release](../../../docs/releases/cn-web-non-thinking-20260923.1.md).

## 10. Independent quick-answer completion (local development)

- [x] 10.1 Persist and emit quick-stage completion before awaiting detailed retrieval or web search, without completing or settling the whole task.
- [x] 10.2 Map stage progress to desktop/mobile answer cards and immediately flush quick text/completion; keep detailed loading, cancellation, and duplicate-submit protection independent.
- [x] 10.3 Add regressions for delayed search, local fallback, stage cancellation, late updates, older responses, and retained simple text; validate, test, and build locally without deployment. See [quick-stage-verification.md](quick-stage-verification.md).

## 11. CN independent quick-stage release (authorized 2026-09-23)

- [x] 11.1 Assemble only the quick-stage changes against the running CN baseline; verify the isolated candidate and prepare a task-record-compatible rollback image.
- [x] 11.2 Retain release artifacts, confirm no live interviews/pages/audio/unfinished answers, and switch only Backend and Web.
- [x] 11.3 Verify deployed code, public endpoints, health and stage behavior; record release and rollback details without changing Global or companion software. See [CN quick-stage release](../../../docs/releases/cn-quick-stage-completion-20260923.1.md).
