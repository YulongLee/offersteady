## Why

Current macOS website artifacts are produced by a local-development packager that permits ad-hoc signing and does not require Apple notarization. The installed Developer ID Application identity now enables a stable, Gatekeeper-compatible release path without changing the companion app's bundle identity or development workflow.

## What Changes

- Add a separate production macOS release command that requires `Developer ID Application: Yulong li (8Y5FAR3TF3)` and never falls back to ad-hoc signing.
- Preserve `com.offersteady.companion` and its Electron helper bundle identifiers.
- Enable Hardened Runtime and timestamped nested signing for the Electron app, frameworks, helpers, dylibs, and Swift capture runtime.
- Use minimal release entitlements while retaining microphone, screen capture, and system-audio usage declarations.
- Require Apple notarization through `notarytool`, staple accepted tickets, build website DMGs, and run codesign, Gatekeeper, and stapler validation.
- Keep existing local-development packaging available and separate from production release.
- Prevent Apple certificates, `.p8` keys, keychain exports, and notarization credentials from entering Git.

## Capabilities

### New Capabilities

- `macos-developer-id-distribution`: Defines the signed, notarized, stapled, verifiable DMG workflow for direct macOS distribution.

### Modified Capabilities

None.

## Impact

- Affects `apps/desktop` build scripts, electron-builder configuration, entitlements, release verification, release documentation, tests, and root ignore rules.
- Does not change desktop runtime behavior, backend APIs, website deployment, persisted data, or the stable bundle identifier.
- Requires an installed Developer ID certificate and external notarization credentials supplied through environment variables or a macOS Keychain profile.
