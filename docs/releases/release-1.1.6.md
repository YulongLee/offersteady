# Release 1.1.6

Release 1.1.6 keeps the realtime publisher alive while macOS audio routes change. It preserves bundle identifier `com.offersteady.companion`, the existing product icon, and realtime protocol `2.0`.

## Fixes

- Debounces bursts of `devicechange` events and retains an explicitly selected microphone while it remains available.
- Switches only the microphone source on the existing publisher instead of rebuilding the shared WebSocket and system-audio runtime.
- Serializes overlapping route changes and converges on the newest available microphone.
- Applies sequence-gap cooldown before changing in-flight frame state, preventing duplicate gap responses from amplifying retransmission.
- Preserves the existing silence-friendly replacement-publisher policy: a control-plane-ready connection does not consume recovery attempts until media is pending.

## Verification

- Desktop type checks passed.
- Desktop tests passed: 25 files, 116 tests.
- Focused hot-switch, transport-gap, and silent-recovery tests passed: 21 tests.
- Production renderer and main-process builds passed.
- `openspec validate stabilize-macos-audio-device-hot-switch --strict` passed.
- Both macOS applications and DMGs passed Developer ID, notarization, Gatekeeper, stapler, and architecture validation.
- The Windows NSIS installer and packaged `OfferSteady.exe` passed structural validation. Windows signing remains truthfully `local-development`.

## Production artifacts

| Target | Artifact | SHA-256 | Signing |
| --- | --- | --- | --- |
| macOS Apple Silicon | `OfferSteady-Companion-1.1.6-macOS-arm64.dmg` | `d84740369292fbe97fe7bd841dabc5bc57178eac9bd2cbab4fc94859f3009458` | Developer ID verified; App/DMG notarized and stapled |
| macOS Intel | `OfferSteady-Companion-1.1.6-macOS-x64.dmg` | `40b5c1717f1f388a7608e2608d1390ff6c543cc896d74bc3e9faa9d2ff1e4749` | Developer ID verified; App/DMG notarized and stapled |
| Windows x64 | `OfferSteady-Companion-Setup-1.1.6-Windows-x64.exe` | `b65a728c6066417fabd97ee9d6622b4a9697f380e4e4212ead6bc2e7499131ff` | Unsigned; explicitly reported as `local-development` |

The 1.1.5 manifest and immutable object paths remain available as rollback. Physical headset removal and reconnection remains the post-release acceptance check with the user.
