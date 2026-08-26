# Release 1.1.7

Release 1.1.7 fixes the production dual-channel audio deadlock observed on companion 1.1.6. It preserves bundle identifier `com.offersteady.companion`, the approved product icon, and realtime protocol `2.0`.

## Fixes

- Tracks microphone and system-audio acknowledgement progress independently so one healthy channel cannot hide a stalled sibling.
- Keeps the oldest unacknowledged deadline stable during continuous speech and replaces a saturated transport through one bounded recovery path.
- Reconnects unexpected WebSocket closures even when the remote close code is 1000, while ignoring stale events from retired sockets.
- Aligns replacement sequences to authoritative resume offsets and discards retired-generation frames instead of filling the send window with stale sequences.
- Clears channel buffers by logical sequence across microphone device identity changes.
- Adds transport-generation, in-flight-window, oldest-unacknowledged-age, and generation-local sequence metadata without audio, transcript content, credentials, or tokens.

## Verification

- Desktop focused recovery tests passed: 7 files, 41 tests.
- Desktop full tests passed: 26 files, 126 tests.
- Desktop type checks and production renderer/main builds passed.
- Backend WebSocket and desktop release compatibility tests passed: 15 tests.
- Synthetic dual-channel soak passed with 4,000 channel frames, an eight-frame microphone stall, unexpected clean close, reconnect, bounded replay, and zero final queue depth.
- `openspec validate fix-dual-channel-ack-deadlock-1-1-7 --strict` passed.
- Both macOS applications and DMGs passed Developer ID, notarization, Gatekeeper, stapler, and architecture validation.
- The Windows NSIS installer and packaged `OfferSteady.exe` passed structural validation. Windows signing remains truthfully `local-development`.

## Production artifacts

| Target | Artifact | SHA-256 | Signing |
| --- | --- | --- | --- |
| macOS Apple Silicon | `OfferSteady-Companion-1.1.7-macOS-arm64.dmg` | `7105f85e7c9f2ea58b6b55ae89d2a085fd55badfeabf5fa4c2f539f6577e5e58` | Developer ID verified; App/DMG notarized and stapled |
| macOS Intel | `OfferSteady-Companion-1.1.7-macOS-x64.dmg` | `fa134e7ef0e9412b3738cae6d8579f0d573e32c6f13bd0f27362ae1cde2641e1` | Developer ID verified; App/DMG notarized and stapled |
| Windows x64 | `OfferSteady-Companion-Setup-1.1.7-Windows-x64.exe` | `e75110451cf22f8a7284c24a434c1907dcca17e77c46b89b77b32251caa5a997` | Unsigned; explicitly reported as `local-development` |

The immutable 1.1.6 objects and local application backup remain available for rollback. Production acceptance records transport metadata only.
