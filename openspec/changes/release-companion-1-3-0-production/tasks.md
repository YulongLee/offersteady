## 1. Release preparation

- [x] 1.1 Confirm 1.3.0 source version, release scripts, signing identity, notarization profile, and current public manifests.
- [x] 1.2 Run desktop tests, typecheck, and builds; record results without exposing secrets.

## 2. Artifact build and verification

- [x] 2.1 Build and verify domestic macOS arm64 and x64 notarized DMGs and metadata.
- [x] 2.2 Build and verify Global macOS arm64 and x64 notarized DMGs and metadata.
- [x] 2.3 Build and verify domestic and Global Windows x64 installers and unsigned metadata.

## 3. Publication

- [x] 3.1 Publish domestic 1.3.0 artifacts and manifest.
- [x] 3.2 Publish Global 1.3.0 artifacts and manifest.
- [x] 3.3 Verify public state, download routes, hashes, and health for both editions.

## 4. Release record

- [x] 4.1 Write a release record with artifact hashes, trust state, verification commands, and rollback references.
- [x] 4.2 Validate this OpenSpec change strictly.
