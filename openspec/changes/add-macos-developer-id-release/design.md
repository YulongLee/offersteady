## Context

The companion is an Electron 42 application with React/Vite renderer code, packaged by electron-builder 26.15.3. It also embeds a Swift executable using AVFoundation and ScreenCaptureKit. The stable app identifier is `com.offersteady.companion`.

The current custom local packager copies Electron.app, edits plists, applies one `codesign --deep` pass, permits ad-hoc fallback, and emits a ZIP marked `local-development`. The current 0.1.16 arm64 artifact is ad-hoc (`TeamIdentifier=not set`), lacks Hardened Runtime, is rejected by Gatekeeper, and has no stapled ticket. The host now has the valid identity `Developer ID Application: Yulong li (8Y5FAR3TF3)`.

## Goals / Non-Goals

**Goals:**

- Add a fail-closed production DMG workflow using the installed Developer ID identity.
- Preserve the app and helper bundle identifiers.
- Sign the complete Electron bundle and native runtime with Hardened Runtime and a trusted timestamp.
- Submit the signed app and the final DMG through Apple `notarytool`, require `Accepted` for both, staple both tickets, and verify the final app and DMG container.
- Keep local development packaging independent and usable.
- Keep notarization secrets outside source control.

**Non-Goals:**

- No Mac App Store, sandbox, provisioning profile, auto-update, website upload, or server deployment.
- No desktop runtime, capture, API, UI, or version behavior changes.
- No certificate/private-key export into the repository.

## Decisions

### Use a dedicated electron-builder release configuration

Production packaging uses a macOS-only release config and wrapper script. The wrapper verifies the exact Developer ID identity, notarization credential completeness, output identity, and final validations. The current custom local packager remains for development.

Alternative considered: extend the custom `--deep` signer. Rejected because nested signing order, entitlements selection, timestamps, notarization, and DMG lifecycle are already handled by electron-builder and `@electron/notarize`.

### Fail closed on signing and notarization

The release config enables `forceCodeSigning`, explicitly selects the Developer ID identity, enables Hardened Runtime, and enables notarization. The wrapper rejects missing credentials and never maps production to `-`, Apple Development, or a local certificate.

An explicit `prepare` command may build a signed, unpacked app for local verification without notarization. It is not a distributable release and does not produce the official DMG.

### Use minimal non-sandbox entitlements

Electron 42 needs `com.apple.security.cs.allow-jit` under Hardened Runtime. `com.apple.security.cs.allow-unsigned-executable-memory` is removed because Electron 12+ does not require it and it increases attack surface. The app is not sandboxed, so microphone, screen recording, and system audio access are represented by existing Info.plist usage descriptions and macOS TCC rather than App Sandbox entitlements.

### Explicitly include the Swift capture runtime in nested signing

The release config lists `Contents/Resources/app/native/macos-capture/OfferSteadyCaptureRuntime` as an additional binary. electron-builder signs Electron helpers, frameworks, dylibs, and this executable before signing the outer app.

### Use App Store Connect API key or Keychain profile authentication

Preferred automation uses `APPLE_API_KEY`, `APPLE_API_KEY_ID`, and `APPLE_API_ISSUER`. The `.p8` path must be absolute and outside the repository. A locally stored `APPLE_KEYCHAIN_PROFILE` is also supported. The release wrapper validates credentials before packaging; no values are persisted in Git.

### Verify the final app contained in the release output

The verifier runs `codesign --verify --deep --strict --verbose=2`, checks Developer ID authority, team ID, Hardened Runtime, and trusted timestamp, then validates the app with Gatekeeper and stapler. After electron-builder creates the DMG, the wrapper signs that container with the same Developer ID and trusted timestamp, submits it as a second notarization, requires `Accepted`, staples the DMG, and validates it with `spctl --assess --type open --context context:primary-signature` and `xcrun stapler validate`. It also enumerates Mach-O executables and libraries and verifies every nested signature.

## Risks / Trade-offs

- [Notarization credentials are not yet present] → keep production DMG generation blocked while allowing a signed prepare build.
- [A nested native binary is missed] → declare it explicitly and enumerate all Mach-O files during verification.
- [Entitlement removal breaks an Electron runtime path] → run packaged smoke tests on both architectures; restore only a specifically proven entitlement.
- [Certificate renewal changes the certificate hash] → select by stable identity name and Team ID, then verify authority/team after each build.
- [Apple service delay] → `notarytool --wait` remains authoritative; do not publish an unstapled fallback artifact.

## Migration Plan

1. Add release config, minimal entitlements, validation scripts, tests, ignore rules, and operator documentation.
2. Build an arm64 signed prepare app with the installed identity and verify nested signatures/Hardened Runtime.
3. Create and securely configure notarization credentials.
4. Run arm64 and x64 production commands to obtain Accepted, stapled DMGs.
5. Publish only after all three final validations pass; rollback by withholding the new DMGs and retaining the previous website entries.

## Open Questions

- Notarization credentials are configured locally through the `OfferSteady-Notary` Keychain profile and are not stored in the repository.
- The Developer ID private key has completed the required local Keychain approval for `/usr/bin/codesign`.
- The x64 Electron executable completed a Rosetta execution smoke check and reported `process.arch=x64`; a physical Intel Mac installation smoke check remains recommended before broad public rollout.
