## Context

`AdminCapacityMonitor` keeps a bounded five-minute request window and currently reports aggregate control, recovery, and SSE timing. The aggregate value is useful for alerting but does not identify the route or whether the request contributes to the user's interaction path. The dashboard already polls the capacity response, so the change can remain additive and preserve existing clients.

## Goals / Non-Goals

**Goals:**

- Attribute recent latency and 5xx events to a normalized route and stable request class.
- Report separate user-facing and telemetry summaries while preserving existing aggregate fields.
- Keep the payload bounded and free of IDs, query strings, request bodies, transcripts, or other personal data.
- Present the new summaries in the existing admin dashboard visual language.

**Non-Goals:**

- Changing interview, ASR, screenshot, provider, or answer-generation behavior.
- Persisting raw request logs or adding a new observability vendor.
- Hiding high latency by changing warning thresholds.

## Decisions

1. **Classify at request-recording time.** Normalize dynamic path segments (session IDs, device IDs, and capture IDs) into route templates and assign each request to `user_api`, `telemetry`, `recovery_snapshot`, or `sse_stream`. This avoids high-cardinality data and lets the existing rolling window produce both aggregate and per-group summaries.
   - *Alternative considered:* parse access logs externally. Rejected because it adds deployment complexity and loses the in-process status code context.

2. **Keep user API P95 separate from telemetry P95.** Existing `apiP95Ms` remains backward compatible, while new fields identify `userApiP95Ms`, `telemetryP95Ms`, and bounded route rows. SSE duration remains separate and is excluded from user API P95.
   - *Alternative considered:* remove telemetry from `apiP95Ms`. Rejected because older clients depend on its current semantics; additive fields allow a gradual dashboard transition.

3. **Expose summaries through the existing capacity response.** Add a `supporting.requestBreakdown` object containing overall class summaries and the slowest bounded routes. The endpoint remains protected by existing admin authentication.
   - *Alternative considered:* add a new endpoint. Rejected for this MVP because it would require another polling path and more authorization surface.

4. **Render a compact diagnostic panel without changing the page layout.** The dashboard shows class-level P95/error counts and a short top-slow-routes list only when data exists; existing cards remain unchanged.

## Risks / Trade-offs

- [High-cardinality route labels] → Normalize IDs and cap route rows to a small fixed number.
- [Metric interpretation changes] → Preserve legacy fields and label the new user/telemetry values explicitly.
- [Monitoring overhead] → Aggregate in memory over the existing bounded deque; do not add per-request network calls.
- [Sensitive data exposure] → Strip query strings and dynamic identifiers; retain only route templates, class names, timing, counts, and status totals.

## Migration Plan

1. Ship backend additive fields and tests.
2. Ship dashboard rendering that tolerates missing breakdown fields for older backends.
3. Verify authenticated capacity, health, and live-session smoke checks.
4. Roll back by restoring the previous backend/web images; no schema migration is required.

## Open Questions

- None for the MVP implementation; route caps and class names are implementation constants and can be tuned from observed production data later.
