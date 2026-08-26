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

All three artifacts were uploaded under immutable 1.1.5 OSS object keys in one publication run. The generated production manifest contains exactly the three aligned targets. Production runtime deployment and real-speech acceptance are recorded after rollout.
