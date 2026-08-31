# Release 1.2.13 Control-plane Tail Latency

Release 1.2.13 reduces companion control-plane request amplification and corrects API latency classification without changing realtime audio, ASR, answers, billing, permissions, layout, or user-facing health presentation.

## Compatibility boundary

- Waiting binding discovery follows the Backend refresh suggestion with a 1-second floor; the existing 2-second live lease cadence remains unchanged.
- Stable `device-status` payloads are suppressed for 15 seconds, while semantic transitions publish immediately and failed posts remain retryable.
- Screenshot request SSE connections survive eligible capture state changes and retain a single main-process owner.
- Realtime and screenshot stream connection durations are reported separately and excluded from ordinary API P95/P99.
- Protocol version 2.0, production endpoints, Bundle ID `com.offersteady.companion`, window layout, icon family, capture pipeline, ASR settings, answer behavior and privacy boundaries are unchanged.

## Verification

- Desktop full suite: 174 tests passed across 31 files.
- Desktop main/renderer typecheck and production build passed.
- Backend focused capacity suite: 8 tests passed.
- Backend full suite: 388 passed and 14 skipped; one existing concurrency timing assertion exceeded its threshold by 16ms under the full-suite load and passed immediately when rerun in isolation.
- Strict OpenSpec validation passed for `reduce-companion-control-plane-tail-latency`.

## Production artifacts

Production artifact sizes, SHA-256 values, signing/notarization results and publication paths are recorded after all three aligned platform packages are built and verified.

## Rollout and rollback

- Publish immutable versioned artifacts before switching the checked-in release manifest.
- Confirm no active interview before replacing the single Backend service.
- PostgreSQL, Redis, Web, Admin and Analytics services are not replaced.
- Rollback restores the prior Backend image and the 1.2.12 release manifest; versioned 1.2.13 objects remain recoverable and no user data is deleted.
