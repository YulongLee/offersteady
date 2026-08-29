## 1. Health State Contract

- [x] 1.1 Add a pure user-facing health classifier for companion runtime and audio source states
- [x] 1.2 Add regression tests for idle, silent, active, recovering, permission-denied and unavailable states

## 2. Desktop Presentation

- [x] 2.1 Apply the classifier to the website connection indicator without changing layout
- [x] 2.2 Apply healthy/fault semantics to audio source lights while preserving real audio levels
- [x] 2.3 Add a restrained green breathing animation with reduced-motion support

## 3. Version and Verification

- [x] 3.1 Bump the desktop workspace and lockfile version from 1.2.11 to 1.2.12
- [x] 3.2 Run desktop typecheck, tests and build
- [x] 3.3 Run strict OpenSpec validation and verify no realtime pipeline configuration changed
- [x] 3.4 Build and launch the local macOS arm64 companion for user testing

## 4. Production Release

- [ ] 4.1 Commit and push the accepted 1.2.12 source baseline
- [ ] 4.2 Build, notarize and verify macOS arm64 and x64 production DMGs
- [ ] 4.3 Build and structurally verify the Windows x64 installer
- [ ] 4.4 Upload immutable artifacts and atomically update the production desktop manifest
- [ ] 4.5 Commit and push the manifest and release record, then deploy the Backend manifest consumer
- [ ] 4.6 Verify production health, manifest versions and byte-range download routes for all three platforms
