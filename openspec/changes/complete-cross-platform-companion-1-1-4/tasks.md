## 1. Brand and Version Correction

- [x] 1.1 Add regressions that pin desktop package and renderer icons to the approved public brand asset instead of checking dimensions alone.
- [x] 1.2 Replace desktop package and renderer icon inputs with approved deterministic assets and visually verify the packaging and in-window variants.
- [x] 1.3 Bump Desktop and lockfile version to 1.1.4 while preserving bundle identifier and realtime protocol 2.0.

## 2. Cross-Platform Build Verification

- [x] 2.1 Run Desktop tests, type checks and production build plus strict OpenSpec and diff validation.
- [x] 2.2 Build and verify Developer ID signed/notarized macOS arm64 and x64 1.1.4 DMGs with matching icon and metadata.
- [x] 2.3 Build and validate the Windows x64 1.1.4 NSIS installer, PE/runtime metadata and truthful unsigned signing state.

## 3. Atomic Production Publication

- [x] 3.1 Upload all three 1.1.4 artifacts in one production publication and generate a complete three-target manifest.
- [ ] 3.2 Commit and deploy the release manifest and release evidence without changing protocol 2.0 or persisting interview content.
- [ ] 3.3 Verify public health, three 1.1.4 manifest entries, macOS verification flags, Windows signing disclosure and byte-range downloads.
