# Global Companion 1.3.6 package checks

This verifier reads local Global packages only. It does not build, launch the
companion, open devices, access production, upload or modify release manifests.
It reuses the existing local verifier's checked archive traversal, ASAR read,
PE/Mach-O parsing, signature-normalized native comparison and exact App/DMG
payload comparison. Global identity and configuration checks remain separate;
the domestic verifier is not changed or relaxed.

Freeze each architecture immediately after its serial build:

```sh
python3 tools/global_companion_1_3_6/verify_packages.py freeze \
  --output artifacts/global-companion-1.3.6-20261102/mac-arm64-source.json
```

A freeze includes all desktop source/resource/native/build-script inputs, the
workspace lock, Vite/TypeScript build configuration and the exact four-field
public Global production runtime configuration. Compiled tests, local runtime
configuration and user/device credentials are rejected. All sources and every
non-native packaged dist byte must match; native code is compared using the
existing signature normalization on disposable copies.

Mac verification requires an official DMG and calls the formal signature,
actual main/helper/native audio-input entitlement, App/DMG Gatekeeper and
stapler verifier with Global bundle identity. It also compares the mounted DMG
App with the verified App and checks Global runtime resources and actual ASAR.

```sh
python3 tools/global_companion_1_3_6/verify_packages.py mac \
  --app 'apps/desktop/release/global/mac-arm64/OfferSteady Companion Global.app' \
  --arch arm64 \
  --artifact apps/desktop/release/global/OfferSteady-Companion-Global-1.3.6-macOS-arm64.dmg \
  --manifest artifacts/global-companion-1.3.6-20261102/mac-arm64-source.json \
  --output artifacts/global-companion-1.3.6-20261102/mac-arm64-package.json
```

Windows uses the prepared `win-unpacked` package, reads its ASAR and exact Global
runtime config, tests both NSIS archives, compares every installed file, checks
actual x64 PE and retains truthful unsigned status after checking both app and
installer certificate tables. The existing trusted 7zz cache is supplied by the
caller; the verifier downloads nothing and executes no packaged code.

```sh
python3 tools/global_companion_1_3_6/verify_packages.py win \
  --package apps/desktop/release/global/win-unpacked \
  --artifact apps/desktop/release/global/OfferSteady-Companion-Global-Setup-1.3.6-Windows-x64.exe \
  --sevenzip /Users/liyulong/Library/Caches/electron-builder/7zip@1.0.0/7zip-darwin-arm64-fti70/bin/7zz \
  --manifest artifacts/global-companion-1.3.6-20261102/windows-x64-source.json \
  --output artifacts/global-companion-1.3.6-20261102/windows-x64-package.json
```

Structural and signature checks do not establish physical-device microphone,
Bluetooth, screen capture, OS permission clicks, real sleep/network recovery or
full online interview acceptance. Those limits remain explicit in every report.
