# Release 1.2.9 Background Realtime Activation

Release 1.2.9 disables Electron background throttling for the companion renderer. The companion normally loses focus when the user enters the interview browser; realtime binding control polls and audio callbacks must continue at their configured cadence in that state.

It also pins a healthy live publisher to its authoritative session binding. A newer unrelated binding cannot silently replace an active live interview, and initial publisher startup no longer presents itself as an audio-gap reconnect. Real recovery after an established transport failure remains visible.

The preparation waiting poll remains 250 milliseconds. This release does not change VAD thresholds, endpointing, provider model behavior, UI layout, icons, or privacy boundaries.

## Acceptance

- With the companion behind the interview browser, a successful live start is observed without the prior one-second renderer clamp.
- Prepared audio sources are promoted without reopening healthy devices.
- No preparation PCM is published.
- A second account cannot take over a device serving a live interview.
- Initial publisher startup remains non-alarming; a real post-healthy transport recovery still reports `reconnecting`.

## Verification State

- Desktop regression suite: 163 tests passed across 29 files; typecheck and production build passed.
- Backend regression suite: 342 passed and 14 skipped. One unrelated load-sensitive timing assertion failed in the full run, then passed three isolated reruns.
- Web regression suite: 306 of 307 tests passed; the remaining pre-existing material-action assertion expected a generic backend-unavailable message while the current UI truthfully showed `文档不存在。`. Typecheck and guarded production build passed.
- Active OpenSpec changes passed strict validation.
- Physical isolated-chain acceptance remains open; the prior user test established live binding stability and terminalization but was not an isolated local first-visible timing measurement.

## Production Artifacts

| Target | Artifact | Bytes | SHA-256 | Verification |
| --- | --- | ---: | --- | --- |
| macOS Apple Silicon | `OfferSteady-Companion-1.2.9-macOS-arm64.dmg` | 126292292 | `dd51a92fa69643e02279b3d847ece88845676ccfcd0927840a620f160e6620f8` | Developer ID verified; App/DMG notarized, stapled, and Gatekeeper accepted |
| macOS Intel | `OfferSteady-Companion-1.2.9-macOS-x64.dmg` | 129836721 | `0fdacee654ab6bee7bee9962afdf036ca87ee76e062e4d7bce3bc8960cd868b1` | Developer ID verified; App/DMG notarized, stapled, and Gatekeeper accepted |
| Windows 10/11 x64 | `OfferSteady-Companion-Setup-1.2.9-Windows-x64.exe` | 102148064 | `e48a3d32ac1ae017bd23f853efa47223d59e7379e13b3fbdb796db6b522567f2` | NSIS payload and x86-64 executable validated; unsigned `local-development` signing status retained |

Both macOS artifacts use `Developer ID Application: Yulong li (8Y5FAR3TF3)`. The release signer excludes sealed Electron resource payloads from per-file timestamp signing while retaining explicit nested signing for `OfferSteadyCaptureRuntime`.

## Production Rollout

- Application source baseline: `33f4899`.
- Pre-rollout server commit: `c355d4d4eee1344df104dafa692a5a65c5819d41`.
- Rollback images: `offersteady-backend:rollback-c355d4d-pre-1.2.9` and `offersteady-web:rollback-c355d4d-pre-1.2.9`.
- Backend and Web switched without recreating PostgreSQL or Redis; public health, billing status, Web state, build manifest, and `/app` returned HTTP 200 after the switch.
- The three versioned artifacts were uploaded before the production manifest was changed; the Backend manifest is the atomic publication boundary.
