## Why

OfferSteady currently publishes only a macOS Apple Silicon test companion, which prevents Intel Mac and Windows users from completing the core microphone, interviewer-audio, and screenshot workflow. The existing Electron shell already contains most cross-platform primitives, so the next release should turn the placeholder platform entries into truthful, downloadable test packages.

## What Changes

- Add a macOS Intel x64 companion package with the same pairing, microphone, system-audio, screenshot, and shortcut behavior as the arm64 package.
- Add a Windows 10/11 x64 companion package using Electron microphone capture, Chromium/WASAPI loopback system-audio capture, screen capture, and the existing backend protocol.
- Make desktop permission and diagnostic copy platform-aware rather than presenting macOS-only instructions on Windows.
- Produce platform-specific package metadata, SHA-256 checksums, and OSS object paths.
- Merge all published desktop packages into one release manifest and expose working download actions on the Web device page.
- Mark unsigned/ad-hoc artifacts as test builds and preserve truthful signing status; this change does not claim Apple notarization or Windows code signing.
- Keep raw audio and screenshots transient under the existing privacy policy.

## Capabilities

### New Capabilities

- `multi-platform-desktop-runtime`: Runtime behavior for macOS Intel and Windows x64 microphone, system-audio, screen capture, permissions, pairing, and diagnostics.
- `multi-platform-desktop-distribution`: Reproducible packaging, metadata, OSS publishing, release-manifest merging, and Web downloads for all supported desktop targets.

## Impact

Affected areas include `apps/desktop` runtime and packaging scripts, Electron builder configuration, `scripts/publish-desktop-release.py`, backend desktop release manifest and download tests, Web download-center copy and tests, OSS release paths, and desktop distribution documentation. No backend realtime protocol or sensitive-data retention policy changes are required.
