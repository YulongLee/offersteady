## 1. Release Preparation

- [x] 1.1 Bump package metadata and release documentation to 1.2.0.
- [x] 1.2 Record the physical 1.1.9 acceptance result, expected no-input-device behavior, and rollback boundary.
- [x] 1.3 Run the full Desktop tests, typecheck, build, Backend compatibility checks, and strict OpenSpec validation.
- [x] 1.4 Commit and push the verified 1.2.0 release source before packaging production artifacts.

## 2. Production Artifacts

- [x] 2.1 Verify the production Apple Developer ID identity and notarization credentials without exposing credentials.
- [x] 2.2 Build, verify, notarize, and staple the macOS arm64 1.2.0 artifact.
- [x] 2.3 Build, verify, notarize, and staple the macOS x64 1.2.0 artifact.
- [x] 2.4 Build and structurally validate the Windows x64 1.2.0 installer with truthful signing metadata.

## 3. Publication and Deployment

- [x] 3.1 Upload immutable artifacts and atomically generate the production release manifest.
- [x] 3.2 Commit, tag, and push the release manifest and final release identity.
- [x] 3.3 Preserve a production rollback point and deploy the Backend manifest update.
- [x] 3.4 Verify public health, web state, 1.2.0 manifest entries, download availability, and artifact hashes.
