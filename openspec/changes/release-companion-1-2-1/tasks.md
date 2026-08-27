## 1. Recovery Patch

- [x] 1.1 Persist and expose authoritative per-channel source generations in the backward-compatible realtime handshake.
- [x] 1.2 Seed replacement Desktop segmenters above the authoritative generation while preserving sequence-offset recovery.
- [x] 1.3 Add Backend and Desktop regression tests for same-session process restart and transient transport recovery.

## 2. Patch Identity and Invariance

- [x] 2.1 Bump Desktop package and lock metadata to 1.2.1 and add privacy-safe release notes.
- [x] 2.2 Verify Bundle ID, product icon, renderer layout, styles, and interview workflow are unchanged from 1.2.0.
- [x] 2.3 Run full Desktop tests, typecheck, build, Backend compatibility checks, and strict OpenSpec validation.

## 3. Production-grade Local Artifacts

- [x] 3.1 Verify the existing Apple Developer ID identity and notarization profile without exposing credentials.
- [x] 3.2 Build, sign, notarize, staple, and verify the macOS arm64 1.2.1 artifact.
- [x] 3.3 Build, sign, notarize, staple, and verify the macOS x64 1.2.1 artifact.
- [x] 3.4 Build and structurally verify Windows x64 1.2.1 with truthful signing metadata.
- [x] 3.5 Report immutable local artifact paths, hashes, architectures, and trust status while leaving production publication unchanged.

## 4. Authorized Production Publication

- [x] 4.1 Re-run release gates, commit and push the verified 1.2.1 source while recording the current production manifest and Backend image as rollback points.
- [x] 4.2 Upload all three immutable 1.2.1 artifacts and atomically generate the production Desktop manifest without deleting 1.2.0 objects.
- [ ] 4.3 Commit, tag, and push the 1.2.1 production manifest and release identity.
- [ ] 4.4 Deploy only the Backend service containing the compatible resume-generation handshake and retain the pre-1.2.1 Backend image.
- [ ] 4.5 Verify internal and public health, web state, all three 1.2.1 entries, HTTP range downloads and hashes, plus a public realtime resume-generation handshake.
- [ ] 4.6 Record production deployment evidence and rollback identifiers in the 1.2.1 release notes.
