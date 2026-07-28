## Context

The desktop companion already uses one Electron shell and one backend protocol for device pairing, realtime audio publishing, screenshots, and global shortcuts. Distribution currently exposes only a macOS Apple Silicon test build. The local Intel packaging command can copy an arm64 Electron runtime into an x64-named archive, and the Windows build inherits a macOS-only native resource and macOS-only permission guidance.

The first cross-platform release remains an unsigned test release. It must be technically usable without claiming Apple notarization or Windows Authenticode signing.

## Goals / Non-Goals

**Goals:**

- Produce architecture-correct macOS Intel x64 and Windows 10/11 x64 test packages.
- Preserve the existing Apple Silicon behavior and online pairing protocol.
- Capture Windows microphone audio with `getUserMedia`, system output with Electron/Chromium loopback, and screenshots with `desktopCapturer`.
- Generate checksummed metadata and merge independently published platform packages into one manifest.
- Present platform-specific installation and permission guidance.

**Non-Goals:**

- Windows ARM64, Linux, or mobile clients.
- Apple notarization, Windows Authenticode signing, or automatic updates.
- A Windows-native audio helper.
- Persisting raw microphone audio, system audio, or screen recordings.

## Decisions

### Keep one Electron application with platform adapters

The renderer remains the shared owner of microphone, display-loopback, screenshot, and backend transport behavior. macOS can retain its native helper where required; Windows uses Electron's display-media request handler with Chromium/WASAPI loopback. This avoids a second protocol implementation and keeps all server behavior unchanged.

Alternative: build a separate .NET Windows client. This was rejected for the current stage because it duplicates pairing, transport, screenshot, and release logic before Windows usage has been validated.

### Build each target with its real architecture

The Swift helper is compiled with an explicit macOS target architecture. Intel Electron is downloaded and packaged by electron-builder with `--x64`; it is never copied from the host Electron installation. Windows is emitted as a portable zip for unsigned testing, while an NSIS command remains available for a future signed production installer.

Alternative: label the host package as x64. This is invalid because filenames and metadata cannot substitute for executable architecture.

### Treat unsigned packages as test releases

Generated metadata uses `local-development`, includes SHA-256 and file size, and sets `developmentOnly`. The download center explains Gatekeeper or Windows SmartScreen behavior. `verified` remains reserved for signed and, on macOS, notarized artifacts.

### Publish platform entries independently

OSS objects use `desktop-releases/{platform}/{architecture}/{version}/{filename}`. Publishing one package replaces only the matching platform and architecture entry in the manifest, preserving other targets.

## Risks / Trade-offs

- [Windows loopback behavior varies by device and driver] -> Show source health honestly, retain microphone/manual/screenshot fallbacks, and perform physical Windows validation before marking the package verified.
- [Unsigned downloads trigger operating-system warnings] -> Label them as test builds and provide explicit installation guidance; do not claim commercial signing.
- [Cross-compilation does not prove runtime behavior] -> Validate artifact architecture locally and require a Windows physical-device smoke test before a production release.
- [Intel helper compilation can fail when an SDK drops x86_64 support] -> Fail packaging rather than falling back to a host-architecture binary.

## Migration Plan

1. Build and inspect macOS Intel and Windows x64 test artifacts.
2. Publish each metadata file independently to OSS.
3. Deploy the merged backend manifest and Web download-center copy.
4. Validate pairing, microphone, system audio, screenshot, and shortcut behavior on physical Intel Mac and Windows devices.
5. Roll back by removing the affected manifest entry; existing Apple Silicon downloads remain unchanged.

## Open Questions

- Which Windows code-signing provider will be used for the first verified installer?
- Whether the verified Windows release should use NSIS only or also retain a portable zip.
