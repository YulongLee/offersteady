## 1. Scope and baseline

- [x] 1.1 Record user production authorization, CN three-platform scope and release acceptance.
- [x] 1.2 Verify actual manifest, runtime components, upload settings and dynamic download paths; preserve rollback baseline.

## 2. Formal artifacts

- [x] 2.1 Set version 1.3.5, run desktop checks and freeze production build without test runtime overrides.
- [x] 2.2 Build and verify signed/notarized/stapled macOS arm64 DMG and metadata.
- [x] 2.3 Build and verify signed/notarized/stapled macOS x64 DMG and metadata.
- [x] 2.4 Build and verify Windows x64 NSIS installer, packaged source and truthful unsigned metadata.

## 3. Publish and verify

- [x] 3.1 Upload all immutable artifacts and validate remote object integrity before any public switch.
- [x] 3.2 Atomically publish the CN manifest and persist restart-safe metadata without deploying backend feature changes.
- [x] 3.3 Verify public three-platform versions and complete downloads, unchanged component lifecycle and existing mock routes.
- [x] 3.4 Record executed validation, known physical-device limits and rollback; run strict spec/link checks.
