## Why

Developer ID signing and Apple notarization are already working for both macOS architectures, but the website release manifest still points to older ZIP artifacts marked `local-development`. Users therefore do not receive the verified, stapled DMGs even though those production artifacts exist.

## What Changes

- Generate publication metadata directly from a verified production DMG instead of reusing local-development ZIP metadata.
- Refuse to publish a macOS production artifact unless Developer ID signing, notarization, stapling, architecture, and checksum validation pass locally.
- Upload the arm64 and Intel x64 DMGs with the correct content type and publish them as `verified` and `notarized` website downloads.
- Preserve the existing Windows release entry and stable macOS bundle identifier.
- Keep desktop runtime, capture behavior, user data, and interview APIs unchanged.

## Capabilities

### New Capabilities
- `notarized-macos-website-distribution`: Covers fail-closed publication of verified macOS DMGs through the website release manifest.

### Modified Capabilities

None.

## Impact

- Affects the macOS release wrapper, desktop publication metadata, OSS publication script, backend desktop release manifest, release tests, and distribution documentation.
- Requires existing local Developer ID and `OfferSteady-Notary` credentials only during build verification; no Apple credentials or private keys are uploaded or committed.
- Website deployment is required to expose the updated manifest after both DMGs are uploaded successfully.
