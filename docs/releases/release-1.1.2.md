# Release 1.1.2

Release 1.1.2 is the bounded replacement-publisher recovery hotfix for the 1.1 desktop line. It preserves bundle identifier `com.offersteady.companion` and realtime protocol `2.0`.

## Fixes

- Keeps publisher recovery single-flight while watchdog and terminal events overlap.
- Requires the current replacement transport to receive an authoritative audio ACK before recovery completes.
- Ignores stale events from superseded transports.
- Stops each failed WebSocket and its capture runtimes before retrying.
- Bounds consecutive replacement-publisher creation and exits the WebSocket recovery path when the budget is exhausted.

## Verification

| Target | Artifact | SHA-256 | Integrity |
| --- | --- | --- | --- |
| macOS Apple Silicon | `OfferSteady-Companion-1.1.2-macOS-arm64.dmg` | `1236a979dcf7e498a1675ddbb37b616f0f1b8216db978f340c0c305f0c5b089b` | Developer ID, App/DMG notarization, stapler and Gatekeeper passed |
| macOS Intel | `OfferSteady-Companion-1.1.2-macOS-x64.dmg` | `01d9d2511e9b0fa318481b8346cc6f735363837bf4785cbbd25b147b5f854759` | Developer ID, App/DMG notarization, stapler and Gatekeeper passed |
| Windows x64 | `OfferSteady-Companion-Setup-1.1.2-Windows-x64.exe` | `62b24df6784fb9d58527b1c0245ea4d4239169bd83ad728c08f1f3f38780e462` | NSIS structure passed; Authenticode remains unavailable |

All three artifacts were uploaded to their versioned production OSS paths. The checked-in Backend manifest is deployed and public routes are verified in the production rollout step.

The production Backend and download manifest were deployed on 2026-08-26. Public health passed, all three download routes redirected to their short-lived OSS objects, and range probes returned HTTP 206. The Apple Silicon build was installed locally as version 1.1.2 and passed strict signature, Gatekeeper and stapler checks before launch.
