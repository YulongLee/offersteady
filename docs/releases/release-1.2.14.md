# Release 1.2.14 Companion Lifecycle Safety

Release 1.2.14 reduces stale Companion control-plane traffic without changing audio capture, realtime ASR, transcript stabilization, quick-answer, screenshot-answer results, billing, permissions, layout or user-facing health presentation.

## Changes

- Allow one Companion process per domestic profile; a second launch restores and focuses the existing window instead of creating duplicate network and capture loops.
- Suspend remote screenshot SSE and fallback polling after explicit terminal 404/409 binding admission responses.
- Resume exactly one screenshot stream owner when a new live binding becomes eligible.
- Retain existing single-flight binding reads, short backend duplicate-read protection and transient network recovery.

## Verification

- Integrated working tree Desktop suite: 184 passed across 33 files.
- Clean domestic release tree Desktop suite: 178 passed across 32 files.
- Backend full suite: 499 passed and 20 skipped.
- Desktop typecheck, production build, artifact validation and strict OpenSpec validation passed.
- No Global Web, payment, authentication or Admin changes are included in the domestic release source.

## Production artifacts

| Target | Artifact | Bytes | SHA-256 | Verification |
| --- | --- | ---: | --- | --- |
| macOS Apple Silicon | `OfferSteady-Companion-1.2.14-macOS-arm64.dmg` | 126302103 | `40e59a2cb5e96e3241be265183c932f3bbeca090295ffc1d5a13944602838ebd` | Developer ID verified; App/DMG notarized, stapled and Gatekeeper accepted |
| macOS Intel | `OfferSteady-Companion-1.2.14-macOS-x64.dmg` | 129943967 | `5fa1108f5b6f1bbe3db2a34e260e727a1904525c8ac4b8879bad75d04a0589b4` | Developer ID verified; App/DMG notarized, stapled and Gatekeeper accepted |
| Windows 10/11 x64 | `OfferSteady-Companion-Setup-1.2.14-Windows-x64.exe` | 102150160 | `77166248ab74a7943b923bd8efbc20d8da851b363d53deae232bc366ba07b746` | NSIS payload and x86-64 application validated; existing unsigned `local-development` status retained |

## Rollout boundary

Publish all immutable versioned artifacts before switching the backend release manifest. Immediately before replacing the domestic backend, confirm no realtime-active interview from recent database activity and runtime transport state. Preserve the prior backend image and 1.2.13 manifest for rollback; do not restart Web, Admin, PostgreSQL, Redis or Analytics.
