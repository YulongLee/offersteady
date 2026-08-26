## Why

Companion 1.1.8 can start with different Electron user-data directories depending on how it is launched, splitting device pairing and diagnostics across two identities. On macOS, a missing Screen & System Audio Recording grant then causes repeated desktop-source failures while the UI can remain connected, leaving computer audio silent and making recovery appear unreliable.

## What Changes

- Pin the packaged companion to one stable, product-owned user-data directory on macOS and Windows.
- Migrate pairing credentials and user settings from the previous product-name directory only when the stable destination does not already contain them.
- Treat denied or unavailable macOS screen/system-audio capture as an explicit degraded state without unhandled promise rejections or repeated failing source acquisition.
- Show an actionable permission message and allow capture to recover after the user grants permission and restarts the companion, while keeping microphone capture isolated.
- Add regression coverage for directory selection, safe migration, permission denial, and capture-handler rejection containment.
- Increment the companion patch version to 1.1.9 and produce a clean local acceptance build without altering the 1.1.8 rollback artifact.

## Capabilities

### New Capabilities

- `stable-companion-runtime-identity`: Stable local runtime identity, safe state migration, and explicit system-audio permission degradation/recovery for the packaged companion.

### Modified Capabilities

None.

## Impact

- Affects the Electron main-process bootstrap, local pairing/settings storage, macOS display-media permission handling, renderer status copy, Desktop tests, release metadata, and distribution documentation.
- Does not change Backend protocol 2.0, ASR models, transcript semantics, API credentials, billing, or raw-audio persistence.
- Migration is local and metadata-only; interview audio, transcripts, screenshots, and personal information are not copied or newly persisted.
