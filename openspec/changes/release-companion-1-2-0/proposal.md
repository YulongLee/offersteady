## Why

The 1.1.9 acceptance candidate has verified stable runtime identity, explicit macOS system-audio permission handling, continuous computer-output capture, and bounded microphone route recovery. It now needs an independently versioned, signed, verifiable production release so customers receive one consistent companion build and 1.1.x remains available for rollback.

## What Changes

- Promote the accepted companion implementation to semantic version 1.2.0.
- Complete full Desktop and compatibility verification before producing release artifacts.
- Build Developer ID signed and notarized macOS Apple Silicon and Intel artifacts.
- Build the Windows x64 installer and truthfully retain its actual signing status.
- Publish immutable artifacts and atomically update the production download manifest only after every required artifact passes validation.
- Deploy the manifest/backend update, verify public health and downloads, and retain the 1.1.8/1.1.9 rollback packages.

## Capabilities

### New Capabilities

- `companion-release-1-2-0`: Version identity, supported-platform packaging, production publication, verification, and rollback contract for companion 1.2.0.

### Modified Capabilities

None.

## Impact

- Affects Desktop package metadata, release documentation, macOS and Windows artifacts, the production desktop download manifest, Git history, and Backend deployment containing that manifest.
- Does not change protocol 2.0, Backend runtime logic, ASR models, prompts, billing, database schema, or raw-audio persistence.
- Release validation records only versions, signatures, hashes, health, and transport counters; no interview audio, transcript text, screenshots, API keys, or personal information are included.
