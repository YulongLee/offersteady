## Context

Global Backend already runs the approved heartbeat projection, desktop heartbeat write coalescing, and decomposed P95 diagnostics. The deployed Global Web source already has five-second non-final transcript telemetry sampling. The remaining observed Global gap is the lack of a state-read coordinator.

## Goals

- Avoid duplicate Global Web state requests while keeping public and authenticated payloads separate.
- Keep mutation and session-transition state reads authoritative through an explicit `force` option.
- Keep the existing non-final transcript-render acknowledgement reduction from regressing or dropping final revisions.
- Preserve caller cancellation semantics and returned-state isolation.

## Non-goals

- No Backend or database changes.
- No server-side redesign of `/api/v1/web/state` in this change.
- No change to transcript rendering, answer generation, billing, authentication, realtime transport, or desktop companion protocols.
- No Global production deployment until the candidate passes focused checks and a separate idle-gated rollout is authorized.

## Design

### Web state coordinator

`BackendPreviewInterviewAdapter.loadState` uses two keys: `public` and `authenticated`. Each key has one in-flight request and a 1.5-second success-only cache. Concurrent callers share the underlying request; each caller receives an independent clone. A caller abort rejects only that caller's wait, while the shared request remains available to other callers. Failed requests are removed without populating the cache. Callers that need authoritative state pass `force: true`.

### Transcript telemetry sampling preservation

The running Global Web already uses a five-second interval tracked both by segment and interview session. This change adds a focused regression for that behavior. Final revisions remain eligible immediately. The existing bounded acknowledgement queue, idempotency set, diagnostics flag, payload shape, and error swallowing remain unchanged.

### Compatibility

The adapter interface gains an optional `force` field. Existing callers continue to work without it. The Global fixture adapter accepts the option for type compatibility. The API endpoint and response contracts are unchanged.

The running Global Web source already references `webSearchStatus` and `webSources`, while the copied release protocol types omit those additive declarations. The candidate adds the missing `WebAnswerSourceReference` and optional `AnswerProvenance` fields as a type-only build alignment; it does not change serialized behavior.

## Verification and rollout

- Run focused adapter and application tests, Web typecheck, production build, strict OpenSpec validation, and whitespace checks.
- Verify the Global source overlay changes only approved Web files.
- A later deployment must build from the running Global Web source, retain the old image, require two consecutive Global idle gates, recreate only Web, and verify the public Global manifest and health endpoints.
