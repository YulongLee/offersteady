## Why

The production 1.1.3 rollout updated only the two macOS artifacts while leaving Windows on 1.1.2, and the desktop package continued to use a previously rejected dark-background icon instead of the approved current brand asset. A commercial companion release must keep supported platforms aligned, make artifact identity unambiguous, and prevent branding regressions before publication.

## What Changes

- Release the realtime publisher recovery correction on macOS Apple Silicon, macOS Intel and Windows x64 as companion version 1.1.4.
- Replace desktop package and in-window icon inputs with the approved current white-background brand icon and make that source authoritative across packaging targets.
- Add deterministic checks for cross-platform version alignment, icon identity, artifact metadata and manifest completeness.
- Build, verify and publish all three platform artifacts in one production manifest update while retaining truthful platform-specific signing states.
- Keep bundle/application identifiers, realtime protocol 2.0, audio privacy behavior and Backend/Web APIs unchanged.

## Capabilities

### New Capabilities

- `cross-platform-companion-release`: Defines aligned supported-platform releases, authoritative desktop branding and atomic production manifest publication.

### Modified Capabilities

None.

## Impact

- Desktop assets, package metadata, macOS production packaging, Windows NSIS packaging and related tests.
- Backend desktop release manifest and public download routes.
- Production OSS artifacts and deployment sequencing.
- No raw audio, transcript, screenshot or personal-data persistence changes.
