## Why

The published CN 1.3.2 macOS packages omit the Hardened Runtime audio-input entitlement. The startup permission request also treats a 2.5-second wait as denial and exposes no recovery action. Users report no microphone permission prompt or settings entry.

## What Changes

- Add and verify audio-input entitlements for the Mac app and its signed capture helpers.
- Preserve pending, granted, denied, restricted and error states; never infer denial from elapsed time.
- Provide a visible Mac-only microphone permission control, independent of backend registration, with safe status refresh and settings navigation.
- Release CN Mac 1.3.3 after automated validation and signed/notarized artifact checks. Explicitly distinguish automated checks from physical Intel clean-install acceptance.
- First freeze all current source to Git. Build this hotfix from the released 1.3.2 companion baseline, excluding unpublished mock capture changes.

## Capabilities

### New Capabilities

- `macos-microphone-permission-recovery`: Reliable first authorization, truthful state, manual recovery and signed release validation.

### Modified Capabilities

None. Existing interview, audio routing, model, billing, identity and retention behavior stays unchanged.

## Impact

Desktop macOS permissions, signing manifests, release checks, tests and CN download metadata only. No backend business code, database, Windows package or international release changes. No audio recording for permission checks; no resetting OS privacy grants, no change of application identity, and no user data in tests.
