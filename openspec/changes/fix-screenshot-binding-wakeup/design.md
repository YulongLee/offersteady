## Context

Companion 1.2.14 suspends its screenshot request stream after HTTP 404 or 409. The renderer continues polling authoritative pairing state, but the main process only resumes the stream when the coarse capture state changes or the app is activated. A binding can become live while capture state remains `capturing`, leaving screenshot requests unclaimed until an unrelated lifecycle event occurs.

## Goals / Non-Goals

**Goals:**
- Wake a suspended screenshot stream as soon as the renderer observes a valid authoritative binding.
- Keep exactly one main-process stream owner and preserve request idempotency.
- Avoid high-frequency retry loops while no live binding exists.
- Preserve current screenshot upload, model, audio, ASR, answer, billing and UI behavior.

**Non-Goals:**
- Changing backend screenshot APIs or SSE payloads.
- Changing model selection, prompts, capture permissions, layout or audio behavior.
- Adding a new background service or production data migration.

## Decisions

### Publish authoritative binding identity to the main process

The renderer will publish `sessionId + bindingId` after every successful binding poll and publish `null` when no valid binding exists. This signal is separate from capture-state publication because binding lifecycle can change without a capture-state transition.

### Make restart decisions with a pure binding policy

The main process will track the last binding key. A valid new key starts/restarts the stream; a valid repeated key restarts only when the stream is suspended; duplicate notifications while healthy are ignored. A missing binding stops the active stream. Generation cancellation remains the single-owner mechanism.

### Keep 404/409 quiet and suspended until authoritative revalidation

404 and 409 remain non-noisy admission failures to prevent request storms. The existing renderer poll is the bounded revalidation path and immediately notifies the main process when the binding is available again. Transport and server failures keep the existing bounded retry behavior.

## Risks / Trade-offs

- Renderer/main IPC can be duplicated by normal polling. The pure transition policy makes duplicates no-ops while the stream is healthy.
- A renderer crash stops binding notifications. Existing renderer recovery and activation paths remain as secondary recovery mechanisms.
- Publishing `null` during a transient request failure could interrupt a healthy stream. The renderer therefore preserves the last identity on request failures and publishes `null` only after a successful response confirms there is no currently valid binding (including stale-only state).

## Migration Plan

1. Ship as Companion 1.2.15 with no backend schema migration.
2. Publish immutable artifacts for macOS arm64, macOS x64 and Windows x64.
3. Update the release manifest and backend only after the zero-active-interview gate passes.
4. If smoke checks fail, restore the previous manifest/backend image; Companion 1.2.14 artifacts remain immutable and available.

## Open Questions

None.
