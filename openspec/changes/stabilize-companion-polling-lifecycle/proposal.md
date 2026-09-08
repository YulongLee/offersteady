## Why

Production diagnostics on 2026-09-04 showed that repeated or stale desktop Companion instances could generate several times the intended connection and screenshot-control request rate. Under concurrent realtime recovery this amplified control-plane traffic and raised ordinary API P95 above one second even though the server returned no 5xx responses.

## What Changes

- Enforce one running desktop Companion instance per product profile and focus the existing window when a second launch is attempted.
- Keep binding checks single-flight and prevent lifecycle transitions from creating overlapping immediate polls.
- Treat terminal screenshot-stream admission responses as an invalid binding, suspend screenshot retries, and resume only after a binding eligibility change.
- Add a bounded server-side duplicate-read shield for identical active-connection checks without changing the authoritative binding state or normal live refresh cadence.
- Add privacy-safe regression and production verification for request rate, ordinary API P95, rapid consecutive interviews, disconnect recovery, and screenshot delivery.
- Preserve the existing audio capture, realtime ASR, transcript, quick-answer, screenshot processing, billing, and user-facing layout behavior.

## Capabilities

### New Capabilities

- `companion-polling-lifecycle-safety`: Defines single-instance ownership, non-overlapping control polling, terminal invalid-binding suspension, and prompt resumption for a new valid binding.
- `companion-control-read-protection`: Defines bounded duplicate-read protection for desktop connection status without weakening realtime freshness or correctness.

### Modified Capabilities

None.

## Impact

- Desktop main-process startup, binding polling policy, and remote screenshot stream lifecycle.
- Backend desktop active-connection read path and its tests.
- Desktop and backend regression suites, production deployment verification, and rollback documentation.
- No new persistence of audio, transcript, screenshot, device content, or personal information.
