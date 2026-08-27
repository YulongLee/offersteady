# Release 1.2.0

Release 1.2.0 promotes the physically accepted 1.1.9 companion candidate to an immutable production release. It preserves bundle identifier `com.offersteady.companion`, the approved product icon, realtime protocol `2.0`, stable local identity, and the existing Backend/Web compatibility boundary.

## Included fixes

- Uses one stable Electron data directory across Finder, `open`, and command-line launches while migrating only allowlisted pairing state from a legacy product-name directory.
- Contains denied or unavailable macOS system-audio capture without retry storms or unhandled promise rejections, while keeping the microphone channel independent.
- Preserves computer-output capture and transport acknowledgements through headset output-device transitions.
- Reconciles overlapping microphone track-ended and device-change recovery so an available replacement input is attached once and a missing input remains an explicit hardware-unavailable state.
- Keeps realtime transcript transport ordering and terminal acknowledgement behavior introduced by the 1.1.8 recovery baseline.

## Physical acceptance

The accepted Apple Silicon candidate retained its pairing identity and ran microphone and system-audio publishers with one listener each before the headset transition. Both sources delivered contiguous frames with matching Backend acknowledgements and zero observed gaps or retries. Removing the headset did not terminate the companion or system-audio publisher. This Mac has no built-in microphone, so removing its only headset correctly leaves no microphone input device; that state is not classified as a crash or capture regression.

Acceptance evidence contains only runtime counters, versions, signing identity, hashes, and health states. It contains no raw audio, transcript text, screenshots, credentials, or personal information.

## Distribution contract

- Version identity is `1.2.0`; artifacts are rebuilt from the committed release source and are never renamed 1.1.x packages.
- macOS Apple Silicon and Intel packages must pass Developer ID signing, Hardened Runtime, notarization, stapling, Gatekeeper, architecture, and SHA-256 checks before publication.
- Windows x64 is structurally validated and reports its actual signing state. If no trusted Windows signing certificate is available, the production metadata and website retain an explicit unsigned warning.
- Immutable objects are uploaded before the production manifest changes. The manifest and Backend deployment remain recoverable to the prior release.

## Production artifacts

| Target | Artifact | Size (bytes) | SHA-256 | Trust state |
| --- | --- | ---: | --- | --- |
| macOS Apple Silicon | `OfferSteady-Companion-1.2.0-macOS-arm64.dmg` | 123038914 | `06dc51f93a3c12819a37d752def037d71e0599ffe04aa91cfe364f532afce4b5` | Developer ID verified, notarized, stapled, Gatekeeper accepted |
| macOS Intel | `OfferSteady-Companion-1.2.0-macOS-x64.dmg` | 126704437 | `7df74754663ba6349d28a87a199fbba67f4e5cf04ba1e1b1eb3465a36215f1d0` | Developer ID verified, notarized, stapled, Gatekeeper accepted |
| Windows 10/11 x64 | `OfferSteady-Companion-Setup-1.2.0-Windows-x64.exe` | 102011744 | `7ef74acb9d1147baf2f17eded149e15396712d3cbfa40291fe1eb1b56b7b7dd7` | Structurally validated; unsigned / `local-development` signing status |

## Rollback

The local 1.1.8 and 1.1.9 packages remain intact. Production rollback restores the prior desktop release manifest and Backend image/commit; it does not delete versioned release objects or either local data directory.

## Production deployment

Production was deployed on 2026-08-27 from manifest commit `b505418508f014e67919b5a87407bbb9f5a9a3c2` and release tag `v1.2.0`. The previous Backend image is retained as `offersteady-backend:rollback-620e786-pre-1.2.0`. Only the Backend container was rebuilt; PostgreSQL, Redis, and Web were not restarted.

Post-deployment verification passed the internal and public health endpoints. The public state API reported all three targets at 1.2.0, both macOS entries as verified and notarized, and Windows as `local-development` and not notarized. All three public download routes returned HTTP 206 for byte-range requests, and full downloads reproduced the SHA-256 values recorded above.
