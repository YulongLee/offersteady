## 1. Baseline and scope

- [x] 1.1 Freeze and push current source and release tag; isolate the released 1.3.2 desktop baseline
- [x] 1.2 Verify existing desktop permission specs and validate this approved change

## 2. Repair

- [x] 2.1 Add audio-input entitlements and enforce actual signed entitlement values in release verification
- [x] 2.2 Replace timed-out denial with truthful OS status and single-flight consent requests
- [x] 2.3 Add a Mac-only permission recovery panel independent of backend registration
- [x] 2.4 Bump desktop and lockfile to 1.3.3 without changing capture or business protocols

## 3. Verification

- [x] 3.1 Add and run regressions for delayed grant, denial, restriction, duplicate requests, failures, focus refresh and stale/unmounted callbacks
- [x] 3.2 Run full desktop tests, typecheck, build and scope review
- [x] 3.3 Build and verify signed/notarized Intel and Apple Silicon DMGs; document physical-device coverage limitations

## 4. CN publication

- [x] 4.1 Publish immutable Mac artifacts to OSS and back up the current CN manifest
- [x] 4.2 Update CN download metadata only; verify versions, hashes, health and unchanged Windows/international entries
- [x] 4.3 Commit and push the repair, update release notes and hand off user acceptance steps

## 5. User-requested original design restoration (local only)

- [x] 5.1 Remove the added permission panel/styles and retain consent recovery without changing the original layout
- [x] 5.2 Add layout/platform isolation regressions and run desktop tests, typecheck and build
- [x] 5.3 Verify original layout/styles, document local-only status and keep publication paused

Local correction verified 2026-10-02: all 38 desktop test files / 223 tests passed, including 22 permission/layout tests; desktop typecheck and production renderer/main build passed. The complete stylesheet matches released 1.3.2 (`fa9db78`) byte-for-byte (SHA-256 `92280192e06984f1a64ca6cf847cf9306d1c2a3080b3273b0c9f7d2ff802f4fb`). Rendered Mac/Windows tests preserve the original three control rows, connection card and six buttons. Permission initialization, offline recovery, focus refresh and the Windows isolation checks passed with synthetic IPC and no real audio/network. No new installed package, physical-device test, OSS upload, server mutation or release publication was performed for this correction. Windows synchronization remains paused; published Mac 1.3.3 files have not been overwritten.

## 6. Approved local repackaging — 1.3.4

- [x] 6.1 Align version/lockfile, preserve old artifacts and rerun desktop regression/typecheck
- [x] 6.2 Build and verify Developer ID signed/notarized arm64 DMG with original design
- [x] 6.3 Build and verify Developer ID signed/notarized x64 DMG with original design
- [x] 6.4 Verify packaged UI/versions/hashes and hand off local artifacts; no online publication

Repackaging completed locally on 2026-10-02 as 1.3.4. Both Mac apps and final DMGs passed Developer ID signature, actual audio-input entitlement, matching executable/helper architecture, Gatekeeper and stapled-ticket validation. Apple accepted arm64 DMG submission `a88bfcd1-2a0b-46e0-9fbf-7b5efab90d0b` and x64 DMG submission `549504f4-c9cf-4df0-a784-651089589b41`. Packaged renderer assets match the restored original-design build on both Mac architectures and Windows. No real microphone permission reset, clean-install Intel/Windows hardware test, backend restart, OSS upload or online metadata switch was performed.

Local artifacts under `apps/desktop/release/`:

| Package | SHA-256 |
| --- | --- |
| `macos-production/OfferSteady-Companion-1.3.4-macOS-arm64.dmg` | `fdc3d494fd65b51e157865844ed67e6c5e643f8587544d26744c24ee39419ae1` |
| `macos-production/OfferSteady-Companion-1.3.4-macOS-x64.dmg` | `4687a3affa2f11aa195b7287ead151c4a3eb256d2ebb8bcee3dc3a2223e379e4` |
| `OfferSteady-Companion-Setup-1.3.4-Windows-x64.exe` | `24eb5aca547757158b9bffc0b78e2f63195d1adafa75b51db6bdccf53f183f53` |

The previous 1.3.3 Mac artifacts remain intact under `apps/desktop/release/archive/macos-production-1.3.3/`, with their published hashes unchanged. Windows remains unsigned (`local-development`); it is not represented as verified. The Windows change's online publication tasks remain deferred.

## 7. Subsequently approved CN online update — 1.3.4

- [x] 7.1 Freeze approved source, back up current manifests and upload/verify all three OSS artifacts
- [x] 7.2 With no live interviews, activate the complete CN manifest and matching metadata-only image without restarting business services
- [x] 7.3 Verify public versions/downloads/hashes/health and unchanged international releases; record and push release

CN publication verified 2026-10-02 after the user's online-update authorization: all three OSS objects were streamed in full and matched their recorded sizes/hashes; all three latest manifests match the complete local manifest. Zero live interviews was checked twice immediately before activation. Public CN entries are all 1.3.4; each download returns 307 and the correct OSS object returns 206 for a range check. Runtime container ID and start time are unchanged and health is normal. Both host source manifests and the metadata-only image match manifest SHA-256 `96e8f45bb6ba380efbbb3747cd5e48be9e48f66a6097dbabf3b9a4ca5f870e43`. International entries and source remain unchanged at 1.3.2. See [release record](../../../docs/releases/cn-desktop-original-layout-1.3.4-20261002.md) for backups, release tag and physical-device acceptance limits.
