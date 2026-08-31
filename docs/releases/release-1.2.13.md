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

| Target | Artifact | Bytes | SHA-256 | Verification |
| --- | --- | ---: | --- | --- |
| macOS Apple Silicon | `OfferSteady-Companion-1.2.13-macOS-arm64.dmg` | 126298991 | `e9b149512bf214e9cdf234cfaadefc170a485bea84f313723eda5af4d70ada44` | Developer ID verified; App/DMG notarized, stapled and Gatekeeper accepted |
| macOS Intel | `OfferSteady-Companion-1.2.13-macOS-x64.dmg` | 129835199 | `ed90d9873869ded60657ed78905af24a7b520ef2c90d3dbd2409d673e7bd686c` | Developer ID verified; App/DMG notarized, stapled and Gatekeeper accepted |
| Windows 10/11 x64 | `OfferSteady-Companion-Setup-1.2.13-Windows-x64.exe` | 102149516 | `910696a06402d52cdcd9180c943bb67b2c2383b3f85e3bc22ee14ddf2fa6f47f` | NSIS payload and x86-64 executable validated; existing unsigned `local-development` signing status retained |

All three artifacts were uploaded to immutable versioned OSS paths before the Backend production manifest changed. The manifest is the atomic website publication boundary.

## Rollout and rollback

- Publish immutable versioned artifacts before switching the checked-in release manifest.
- Accepted source baseline: `66b422f`.
- Confirm no active interview before replacing the single Backend service.
- PostgreSQL, Redis, Web, Admin and Analytics services are not replaced.
- Rollback restores the prior Backend image and the 1.2.12 release manifest; versioned 1.2.13 objects remain recoverable and no user data is deleted.

## Production verification

- Production source and manifest commit: `5d9df60`.
- Previous Backend image retained as `offersteady-backend:rollback-e75abc3-pre-1.2.13`.
- Active interview count was zero immediately before the single Backend replacement.
- Backend became healthy; PostgreSQL, Redis, Web, Admin and Analytics container identities remained unchanged.
- `/healthz`, `/app`, `/api/v1/web/state` and `/offersteady-build.json` returned HTTP 200.
- The public manifest reported macOS arm64, macOS x64 and Windows x64 at 1.2.13.
- All three public download routes returned HTTP 206 for a one-byte range and advertised totals matching the release manifest.
- The first privacy-safe post-rollout log window contained 552 requests, ordinary API P95 294.15ms, P99 441.41ms and zero server errors. This short window is a smoke result, not a long-term capacity baseline.
- Existing 1.2.12 clients continue their old polling cadence until upgraded; the request-volume benefit is expected only as 1.2.13 adoption increases.
