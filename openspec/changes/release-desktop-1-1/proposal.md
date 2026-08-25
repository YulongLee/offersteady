## Why

The current desktop fixes and realtime subtitle diagnostics have passed their focused verification but the public download manifest still serves different legacy versions for macOS and Windows. A single Release 1.1 baseline is needed before the next optimization cycle.

## What Changes

- Set the desktop companion product version to 1.1.0 for macOS Apple Silicon, macOS Intel, and Windows x64.
- Preserve the stable macOS Bundle Identifier and existing realtime/backend protocol.
- Build, sign, notarize, staple, and verify both macOS DMGs through the existing Developer ID production flow.
- Build and validate the Windows x64 NSIS installer through the existing Windows distribution flow.
- Publish all three artifacts to the desktop release manifest, deploy the current Backend/Web release, and create the Git tag `release-1.1`.

## Capabilities

### Modified Capabilities

- `desktop-release-baseline`: all supported desktop downloads expose the same Release 1.1 product baseline without changing runtime contracts.

## Impact

- Affected code: desktop package metadata, generated release artifacts, desktop release manifest, and release documentation.
- Affected operations: OSS desktop artifact publication, Git push/tag, and production Backend/Web deployment.
- No database migration and no Bundle Identifier or realtime protocol change.
