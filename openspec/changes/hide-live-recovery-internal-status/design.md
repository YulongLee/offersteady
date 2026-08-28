## Context

The Web adapter currently overrides a reported `capturing` state with `reconnecting` whenever Backend runtime readiness becomes `preparing`. Runtime readiness can become `preparing` after a freshness timeout during ordinary silence, so the live page can show a prominent recovery alert while the desktop continues to report healthy capture. The page also renders any genuine `reconnecting` state as a global alert with a retry action, exposing an internal self-healing transition during a high-focus interview.

## Goals / Non-Goals

**Goals:**

- Prevent silence or stale readiness from being interpreted as a device reconnect.
- Keep automatically recoverable reconnect transitions out of the global live-page alert area.
- Preserve internal state, diagnostics, and automatic recovery.
- Preserve existing permission and unrecoverable-error notices.

**Non-Goals:**

- Changing Backend or desktop recovery protocols.
- Hiding permission failures or unrecoverable capture errors.
- Redesigning the live workspace or companion.
- Changing ASR endpointing, transcript timing, or release packaging.

## Decisions

1. The adapter will trust the explicit desktop capture state while it is `capturing`; runtime `preparing` will no longer override it to `reconnecting`. Runtime `degraded` may still produce an error state because it is an explicit failure signal. This separates audio activity freshness from transport health. The alternative—extending the freshness TTL—would only delay the same false alert.
2. The live page will present `reconnecting` as an active interview in user-facing status, controls, and footer, and will not render a global alert. The underlying state remains available in application state for diagnostics and recovery logic. The alternative—only removing the banner—would leave contradictory “reconnecting” or “waiting to start” text elsewhere on the same page.
3. `permission-required` and `error` continue to render their existing global notices because they require user action or make capture unavailable. This prevents silent failure while removing only non-actionable noise.
4. Regression tests will assert both layers: adapter mapping must not synthesize reconnect from healthy capture plus preparing readiness, and application rendering must omit reconnect alerts while retaining actionable notices.

## Risks / Trade-offs

- [A prolonged reconnect can be invisible to the user] → Internal telemetry and diagnostics retain the state; explicit unrecoverable failure must transition to `error`, which remains visible.
- [A prolonged recovery is not visible in the interview UI] → The internal state remains observable to support and must promote to an actionable `error` if automatic recovery is exhausted.
- [Backend can continue emitting ambiguous preparation readiness in live mode] → The Web no longer treats that field as transport truth; Backend semantic cleanup can follow independently without blocking this user-facing defect fix.

## Migration Plan

1. Ship the Web-only behavior and regression tests without protocol changes.
2. Verify permission and error notices remain actionable and reconnect alerts are absent.
3. Roll back the Web artifact if capture failure visibility regresses; Backend and desktop require no rollback.

## Open Questions

None for this focused fix.
