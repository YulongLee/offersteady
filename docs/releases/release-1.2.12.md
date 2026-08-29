# Release 1.2.12 Companion Health Presentation

Release 1.2.12 simplifies the desktop companion's user-facing health presentation without changing its realtime capture or interview protocols. Registered idle devices, active interviews, silent available channels, and transient automatic recovery use the same green visual language. Confirmed service, permission, unsupported-source, and device failures remain red and actionable. Audio meters continue to display only measured signal levels.

## Compatibility boundary

- Desktop renderer presentation and version metadata changed.
- Audio capture, frame cadence, WebSocket transport, ASR, transcript delivery, screenshot capture, device registration, and session binding protocols are unchanged.
- The approved window layout, icon family, product name, Bundle ID `com.offersteady.companion`, production endpoints, and realtime protocol 2.0 are preserved.
- macOS Apple Silicon, macOS Intel, and Windows 10/11 x64 share the same renderer implementation.

## Verification

- Desktop typecheck and production main/renderer build passed.
- Desktop full suite: 168 tests passed across 29 files.
- Health presentation regressions cover registered idle, active capture, silent channels, transient recovery, permission denial, unsupported sources, unavailable devices, and service failure.
- Strict OpenSpec validation passed for `simplify-companion-health-indicator`.
- Diff boundary verification confirmed no desktop audio, Backend realtime, Web realtime, or protocol implementation files changed.
- The accepted Apple Silicon 1.2.12 local build was launched before production packaging.

## Production artifacts

| Target | Artifact | Bytes | SHA-256 | Verification |
| --- | --- | ---: | --- | --- |
| macOS Apple Silicon | `OfferSteady-Companion-1.2.12-macOS-arm64.dmg` | 126293062 | `53b61aca716b8655e43a164591b52a9d0e8f9a80f31efb64489265fd8049caf9` | Developer ID verified; App/DMG notarized, stapled, and Gatekeeper accepted |
| macOS Intel | `OfferSteady-Companion-1.2.12-macOS-x64.dmg` | 129837645 | `9c19ef2fa9f56ac17a46ba2c44269a47ba4d73374c902500f760aff787a44141` | Developer ID verified; App/DMG notarized, stapled, and Gatekeeper accepted |
| Windows 10/11 x64 | `OfferSteady-Companion-Setup-1.2.12-Windows-x64.exe` | 102148681 | `f567ba27b9f47f0098fadd136aa12d196a802e2024c7045ca3c214582d505e9b` | NSIS payload and x86-64 executable validated; existing unsigned `local-development` signing status retained |

All three artifacts were uploaded to immutable versioned OSS paths before the Backend production manifest changed. The manifest is the atomic website publication boundary.

## Rollout and rollback

- Accepted source baseline: `607245d`.
- Deploy only the Backend manifest consumer; PostgreSQL, Redis, Web, Admin, and realtime configuration remain unchanged.
- Verify public health, Web state, all three manifest versions, and HTTP byte-range download routes after deployment.
- Rollback restores the previous tracked desktop release manifest and rebuilds Backend only. Versioned OSS objects are retained, and no user data is removed.
