## Why

The published CN 1.3.2 macOS packages omit the Hardened Runtime audio-input entitlement. The startup permission request also treats a 2.5-second wait as denial and exposes no recovery action. Users report no microphone permission prompt or settings entry.

## What Changes

- Add and verify audio-input entitlements for the Mac app and its signed capture helpers.
- Preserve pending, granted, denied, restricted and error states; never infer denial from elapsed time.
- Keep Mac-only microphone authorization independent of backend registration, with safe status refresh and recovery through the existing microphone control and OS settings. Preserve the original assistant design.
- Release CN Mac 1.3.3 after automated validation and signed/notarized artifact checks. Explicitly distinguish automated checks from physical Intel clean-install acceptance.
- First freeze all current source to Git. Build this hotfix from the released 1.3.2 companion baseline, excluding unpublished mock capture changes.

## Capabilities

### New Capabilities

- `macos-microphone-permission-recovery`: Reliable first authorization, truthful state, manual recovery and signed release validation.

### Modified Capabilities

None. Existing interview, audio routing, model, billing, identity and retention behavior stays unchanged.

## Impact

Desktop macOS permissions, signing manifests, release checks, tests and CN download metadata only. No backend business code, database, Windows package or international release changes. No audio recording for permission checks; no resetting OS privacy grants, no change of application identity, and no user data in tests.

## User correction — 2026-10-02

After the 1.3.3 Mac publication, the user rejected the added permission panel and explicitly required the original assistant design. The follow-up removes that panel and its styles while retaining the entitlement and consent fixes. Validate locally; package publication is paused and immutable published 1.3.3 artifacts must not be overwritten.

The user subsequently requested repackaging. Build the corrected Mac artifacts as 1.3.4, with Developer ID signing and Apple notarization, and preserve the existing 1.3.3 artifacts. This request resumes packaging only, not OSS publication or server changes. The Windows package is covered by `sync-cn-windows-companion-133`, retargeted to the same 1.3.4 version.

After accepting the three local packages, the user explicitly requested the online update. Publish CN 1.3.4 Mac packages together with the separately approved Windows 1.3.4 package. Back up the current manifests, verify full OSS hashes, and activate download metadata with no business service restart when no interview is live. Preserve international releases.
