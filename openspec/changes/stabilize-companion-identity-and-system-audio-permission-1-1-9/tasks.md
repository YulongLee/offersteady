## 1. Stable Runtime Identity

- [x] 1.1 Add tested stable user-data path resolution for packaged and development launches
- [x] 1.2 Add allowlisted, non-overwriting migration for pairing identity, encrypted credential, and shortcut settings
- [x] 1.3 Bootstrap the stable path before Electron session and local-store initialization

## 2. Permission Failure Containment

- [x] 2.1 Add a typed macOS screen/system-audio permission gate before display-source acquisition
- [x] 2.2 Contain display-source and callback rejection paths without unhandled promise rejections or retry storms
- [x] 2.3 Expose actionable system-audio permission state while preserving microphone capture

## 3. Release and Acceptance

- [x] 3.1 Increment companion metadata to 1.1.9 and document the release boundary and rollback
- [x] 3.2 Run focused and full Desktop tests, typecheck, build, and strict OpenSpec validation
- [x] 3.3 Build and install a clean macOS 1.1.9 companion without deleting 1.1.8 rollback artifacts
- [x] 3.4 Verify stable pairing identity, granted system-audio capture, Backend acknowledgements, and headset transition on the physical Mac
