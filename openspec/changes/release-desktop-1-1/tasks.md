## 1. Release Baseline

- [x] 1.1 Set the desktop version to 1.1.0 without changing the Bundle Identifier
- [x] 1.2 Record the current Backend, Web, and Desktop change scope

## 2. Verification

- [x] 2.1 Run Backend and Web tests, type checks, and production builds
- [x] 2.2 Run Desktop tests, type check, build, and release configuration validation
- [x] 2.3 Validate this OpenSpec change strictly

## 3. Desktop Artifacts

- [x] 3.1 Build and verify the signed/notarized macOS arm64 DMG
- [x] 3.2 Build and verify the signed/notarized macOS x64 DMG
- [x] 3.3 Build and validate the Windows x64 NSIS installer
- [x] 3.4 Publish all three artifacts and update the release manifest

## 4. Git and Production

- [ ] 4.1 Commit and push the verified release to main
- [ ] 4.2 Create and push the `release-1.1` tag
- [ ] 4.3 Deploy Backend/Web and the desktop release manifest to production
- [ ] 4.4 Verify production health, runtime pages, and all three downloads
