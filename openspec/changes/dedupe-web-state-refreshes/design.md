## Context

`BackendPreviewInterviewAdapter.loadState` currently sends one `/api/v1/web/state` request for every caller. The provider initializes the app, login recovery, library processing polling, live-page reconciliation, and post-mutation refreshes through the same method, so adjacent calls can fetch the same large aggregate state more than once. The change is Web-only and must preserve fresh reads after operations that mutate or charge state.

## Goals / Non-Goals

**Goals:**

- Merge concurrent state reads that use the same authentication mode into one request.
- Reuse a successful state result for a very short in-memory window for ordinary reads, reducing sequential duplicate reads during page transitions and adjacent effects.
- Allow callers that completed a mutation or need authoritative billing/session data to bypass the reuse window.
- Keep public and authenticated state caches isolated, avoid caching failures, and preserve abort behavior for the caller that initiated the shared request.

**Non-Goals:**

- Do not change the `/api/v1/web/state` backend response or its database query plan.
- Do not cache state in localStorage, IndexedDB, Redis, or any server-side store.
- Do not alter heartbeat cadence, SSE subscriptions, interview audio, answer generation, billing rules, or session ownership.
- Do not deploy or change production infrastructure in this change.

## Decisions

1. **Deduplicate in the adapter boundary.** Keep all existing UI call sites on `loadState`; a small request coordinator in `BackendPreviewInterviewAdapter` protects callers that do not know about one another and avoids route-specific partial fixes.
2. **Use separate public/authenticated keys.** The `auth: false` public bootstrap request must never share a response with an authenticated request, even when both run in the same tab.
3. **Use a short success-only TTL.** Ordinary reads may reuse a successful response for 1.5 seconds. This covers adjacent effects and route transitions while keeping session, material, and billing changes visible quickly. Mutating flows call `force: true` to bypass and replace the cached entry.
4. **Share in-flight promises, not AbortControllers.** The coordinator owns the network request. A caller abort only stops waiting for that caller; it must not cancel a request other callers are sharing. The shared request is removed on rejection, and the failure is never cached.
5. **Return cloned state values.** `WebAppState` is mutable in React callers. Each consumer receives a structured clone of a successful cached result so one caller cannot mutate the cached object seen by another caller.
6. **Make freshness explicit.** Extend the adapter option type with `force?: boolean`. Existing callers keep the default deduplicated behavior; post-mutation refreshes and billing/session transitions opt into `force: true`.

## Risks / Trade-offs

- [Risk] A state change made by another tab can remain hidden for up to 1.5 seconds → Mitigation: keep the TTL short and preserve force refresh for local mutations; live session events and heartbeats remain independent.
- [Risk] Cloning a large state payload adds client CPU → Mitigation: clone only successful cache hits/shared results and measure tests; the cost is local and bounded by the existing aggregate payload.
- [Risk] A caller aborting does not cancel the shared request → Mitigation: the request still has the client transport timeout and is removed on completion/rejection; this prevents duplicate retries from multiple callers.
- [Risk] A mutation caller forgets `force: true` → Mitigation: add focused tests and update every known mutation refresh call in the Web code.

## Migration Plan

1. Add the coordinator and focused adapter tests.
2. Update mutation and billing refresh call sites to request authoritative state.
3. Run Web tests, typecheck, production build, and strict OpenSpec validation locally.
4. During an idle CN window, deploy Web only, monitor user/telemetry P95 and request count, and roll back the Web artifact if errors or stale-state reports increase.

## Open Questions

- Whether the production Admin dashboard exposes enough route-level data to measure the reduction directly; if not, use reverse-proxy request counts and Backend capacity samples before and after the idle-window rollout.
