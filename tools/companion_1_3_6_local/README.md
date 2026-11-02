# Companion 1.3.6 local package checks

These tools only freeze/read local build bytes and validate packages. They do
not build the companion, launch it, open a microphone, contact the backend,
upload to OSS/Apple, update a download manifest, install an app or run Git.
All package verification writes are confined to requested JSON outputs and
new disposable extraction/signature-normalization directories.

Use the approved source on `codex/companion-1-3-6-local`. The immutable preceding
baseline remains `release-cn-20261101.1`; the new helper is not that release.

## Build arrangement

Complete source/test/type checks first. Bump `apps/desktop/package.json` and
the workspace lock to `1.3.6`. Keep Electron, domestic bundle/team identity,
protocol and default CN endpoints. Unset unintended edition/API/workspace
override environment variables for packaging. Never include
`local-test-runtime.json` or `global-runtime-config.json` in these packages.

**Build each architecture serially.** The existing Mac script rewrites shared
`dist/native`; concurrent ARM/Intel builds can mix the native capture runtime.
After each build, freeze and verify that architecture before building another.

The old `package-local-mac.mjs` refers to a missing local entitlement file.
Use the existing signed **prepare-only** path, which does not submit the App
for notarization or publish anything:

```sh
node apps/desktop/scripts/package-release-mac.mjs arm64 --prepare-only
# Later, after freezing/validating ARM:
node apps/desktop/scripts/package-release-mac.mjs x64 --prepare-only
```

This requires the existing Developer ID signing identity. The main and Helper
audio-input entitlement must be checked on their **actual signatures**. Do not
reset OS privacy permissions or change the bundle ID to work around a failure.
The script logs the final App path under `apps/desktop/release/macos-production`.

The existing Windows path builds an x64 portable directory and NSIS installer:

```sh
npm run package:win:installer:x64 -w @offersteady/desktop
```

It can use the existing `OFFERSTEADY_WINDOWS_ELECTRON_DIR` official cached
runtime. Treat the Windows package as unsigned unless Authenticode is actually
validated. The NSIS outer stub may be x86; the installed `OfferSteady.exe` must
be x64, and the installer must carry exactly the checked `app-64.7z` payload.

## Freeze tested inputs

Run after each build. Use a different manifest for each architecture:

```sh
/Users/liyulong/anaconda3/bin/python tools/companion_1_3_6_local/verify_packages.py freeze-dist \
  --output artifacts/companion-1.3.6-local/mac-arm64-source.json
```

`freeze-dist` hashes all desktop source/resources/build scripts/configuration,
the workspace lock and every built `dist` file. It requires version `1.3.6`,
the main/renderer entries and both domestic HTTPS defaults. Mac native bytes
are also frozen after signature removal **on disposable copies**. Apple leaves
signing-expanded `__LINKEDIT.vmsize` behind, so this derived virtual allocation
is normalized to the remaining file size/page alignment. On unsigned Intel
builds codesign also rounds the former signature offset to 16 bytes; canonical
forms add at most 15 zeros and update the derived `__LINKEDIT.filesize`, preserving
all original code/data instead of trimming them. Trailing zero padding is
normalized too. All code/data, UUID, offsets and other load commands remain
compared, and unexpected trailing nonzero data fails. Developer ID signing
changes signature/linkedit bytes, so comparing the whole signed hash to the
pre-signing build would be incorrect. Input files are never modified. Verifiers
later reject changed source or packaged dist.

## Mac App and local archive

First verify the signed App. The command reads its ASAR without executing any
contents, compares every packaged dist file, checks all main/Helper/native
architectures, version/identity, native payload, and invokes the existing
strict signature and actual audio-input/JIT entitlement verifier:

```sh
/Users/liyulong/anaconda3/bin/python tools/companion_1_3_6_local/verify_packages.py verify-mac \
  --app 'apps/desktop/release/macos-production/mac-arm64/面试稳伴随程序.app' \
  --arch arm64 \
  --manifest artifacts/companion-1.3.6-local/mac-arm64-source.json \
  --output artifacts/companion-1.3.6-local/mac-arm64-package.json
```

The same CLI accepts an optional local ZIP or DMG via `--artifact`. For ZIP it
checks CRC and paths, extracts with `ditto` to a disposable directory and
compares the entire App including framework links. For DMG it runs `hdiutil
verify`, mounts **read-only/nobrowse/noautoopen**, compares the App and detaches
it. Only the App payload must match; a DMG may additionally contain an
Applications shortcut or installer background.

Root packaging may create a local ZIP directly from the verified App:

```sh
ditto -c -k --sequesterRsrc --keepParent \
  'apps/desktop/release/macos-production/mac-arm64/面试稳伴随程序.app' \
  apps/desktop/release/OfferSteady-Companion-1.3.6-Local-macOS-arm64.zip
```

Then repeat `verify-mac` with
`--artifact apps/desktop/release/OfferSteady-Companion-1.3.6-Local-macOS-arm64.zip`.
Use the App path reported by the x64 build for Intel. A signed local App/ZIP/DMG
is still **unnotarized**; this workflow does not claim Gatekeeper/stapler checks.
No instruction disables Gatekeeper or bypasses a system warning.

## Windows installer and exact inner payload

Freeze the Windows build, then supply the existing trusted 7zz executable:

```sh
/Users/liyulong/anaconda3/bin/python tools/companion_1_3_6_local/verify_packages.py freeze-dist \
  --output artifacts/companion-1.3.6-local/windows-x64-source.json

/Users/liyulong/anaconda3/bin/python tools/companion_1_3_6_local/verify_packages.py verify-win \
  --package apps/desktop/release/win-x64/OfferSteady-Companion-1.3.6-Windows-x64 \
  --installer apps/desktop/release/OfferSteady-Companion-Setup-1.3.6-Windows-x64.exe \
  --sevenzip /absolute/path/to/existing/trusted/7zz \
  --manifest artifacts/companion-1.3.6-local/windows-x64-source.json \
  --output artifacts/companion-1.3.6-local/windows-x64-package.json
```

An existing Electron Builder cache on this machine contains
`~/Library/Caches/electron-builder/7zip@1.0.0/7zip-darwin-arm64-fti70/bin/7zz`.
The caller verifies/selects its existing trusted runtime, rather than this tool
downloading a replacement. The CLI tests outer and inner archives, rejects
unsafe member paths/links before extraction, verifies real PE machine/header
fields and compares **all** extracted installed files with the prepared package.
Nothing from the archive is executed.

## Evidence and limits

Each successful package JSON includes artifact size/SHA-256 when supplied,
source manifest SHA-256, exact dist checks, architecture and truthful signing
status. Validation does not prove microphone/loopback hardware, Bluetooth,
OS prompt handling, hidden capture continuity or complete online interviews.
These require the user's explicit device testing after installing locally.
The unchanged official 1.3.5 remains the production download.

Tool regression checks use temporary synthetic payloads only:

```sh
/Users/liyulong/anaconda3/bin/python -m unittest discover \
  -s tools/companion_1_3_6_local -p 'test_*.py' -v
node --check tools/companion_1_3_6_local/asar_inventory.mjs
```
