## 1. Production publication metadata

- [x] 1.1 Generate verified DMG metadata after strict macOS release validation for arm64 and x64.
- [x] 1.2 Make the OSS publisher preserve verified signing state, enforce notarized DMGs for macOS production, and use the DMG content type.
- [x] 1.3 Add regression tests for fail-closed production publication and manifest entry preservation.

## 2. Verification and publication

- [x] 2.1 Run desktop and backend tests plus strict OpenSpec validation.
- [x] 2.2 Revalidate both 0.1.16 production DMGs and generate checksum-backed publication metadata.
- [x] 2.3 Upload both DMGs, verify the manifest preserves Windows, then commit and deploy the manifest without changing desktop runtime code.
- [x] 2.4 Verify the public arm64 and x64 download redirects, downloaded checksums, and DMG Gatekeeper/stapler status.
