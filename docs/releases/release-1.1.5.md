# Release 1.1.5

Release 1.1.5 reduces microphone end-of-speech latency and closes abandoned realtime transcript partials. It preserves bundle identifier `com.offersteady.companion` and realtime protocol `2.0`.

## Corrections

- Uses an adaptive ambient threshold plus a bounded turn-peak release gate so residual microphone noise cannot refresh speech indefinitely.
- Reduces the commercial microphone tail from 700 ms to 500 ms while retaining tail resume and the 12-second hard turn boundary.
- Publishes a terminal transcript event when a provider final is suppressed and marks a prior partial incomplete when a new segment supersedes it.
- Enables the four-second backend source watchdog in production Compose and aligns the Web stale-partial presentation boundary to four seconds.
- Keeps incomplete and reconciled display terminals outside answer generation, context insertion, usage duplication, and billing.

## Verification

- Focused regressions: Desktop 29, Web 7, Backend 3 passed.
- Full suites: Admin 34, API 90, Desktop 112, Web 300, Protocol 31 and Backend 327 passed; Backend retained 14 existing conditional skips.
- Workspace type checks, production Desktop/Web builds, OpenSpec strict validation, and diff checks passed.
- Both macOS apps and DMGs passed Developer ID signing, Apple notarization, stapler, Gatekeeper, and 16-component codesign verification.
- Windows NSIS validation confirmed the 1.1.5 installer and packaged `OfferSteady.exe`; signing metadata remains truthfully `local-development`, `notarized: false`.

## Production artifacts

| Target | Artifact | SHA-256 | Security state |
| --- | --- | --- | --- |
| macOS Apple Silicon | `OfferSteady-Companion-1.1.5-macOS-arm64.dmg` | `f07b036e9601f9c86ce67e2471e2b59eaf65c1aa8d2e266cdb15ee5f7c3dde49` | Developer ID verified; App/DMG notarized and stapled |
| macOS Intel | `OfferSteady-Companion-1.1.5-macOS-x64.dmg` | `89866188c4a74a1c5b328d65c984c3512cff1157f7afda6919628126850ee9e5` | Developer ID verified; App/DMG notarized and stapled |
| Windows x64 | `OfferSteady-Companion-Setup-1.1.5-Windows-x64.exe` | `60d51c953ed4d9f4cd9170cddda456165f55177bb00a9ca5f64f7b7ac4dbfea6` | Unsigned; explicitly reported as `local-development` |

All three artifacts were uploaded under immutable 1.1.5 OSS object keys in one publication run. The generated production manifest contains exactly the three aligned targets.

## Production rollout

- Runtime source commit: `dc8493c36d77ed49127b35f10440ab1792abc6c4`.
- Backend image: `sha256:8c087a5b27c41c34384ea2034f90d60a70f2ce9dc361bee76e91f45267e001e8`.
- Web image: `sha256:578aff314bd706a41156a0226934123406f87eb5e9f47ccec61a6e7d80be4c9c` with main asset `assets/main-DZs0_YMH.js`.
- Rollback source: `cfe5ede200cd3ce164e50573ba83812dbb6159e3`; rollback Backend/Web images retain the `rollback-cfe5ede-pre-finalization` tags.
- Production configuration reports source watchdog enabled with a 4.0-second deadline and 0.5-second poll interval.
- Public `/healthz`, `/api/v1/web/state`, and `/offersteady-build.json` returned HTTP 200. All three 1.1.5 download routes returned HTTP 206 for byte-range probes and reported the expected immutable checksums.
- Post-switch Backend logs contained zero matching error/traceback entries. Metadata-only realtime metrics reported protocol 2.0, raw audio persistence disabled, zero queued frames, and no active desktop transport at the time of the probe.
- The unchanged Admin image was retained after its unnecessary rebuild hit the known npm optional native-binding issue; Admin was not part of this change and remained running.

Real microphone speech-stop acceptance remains a user-operated production check because no active desktop transport was present during the metadata-only probe.
