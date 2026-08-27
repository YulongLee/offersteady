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

## Rollback

The local 1.1.8 and 1.1.9 packages remain intact. Production rollback restores the prior desktop release manifest and Backend image/commit; it does not delete versioned release objects or either local data directory.
