## Context

The realtime recovery correction is source-compatible across Electron macOS and Windows, but the 1.1.3 production rollout only replaced macOS entries. Windows remained on 1.1.2. Desktop packaging also consumes a desktop-specific dark icon while the approved current public brand icon is a white-background asset, and existing tests validate dimensions rather than identity against the brand source. Because 1.1.3 artifacts are already public, replacing their bytes in place would make caches and recorded checksums ambiguous.

## Goals / Non-Goals

**Goals:**

- Publish one traceable 1.1.4 release across macOS arm64, macOS x64 and Windows x64.
- Use one approved raster brand source for the packaged application and renderer brand mark.
- Preserve truthful signing and notarization metadata per platform.
- Prevent partial platform publication and icon drift through automated checks.

**Non-Goals:**

- No realtime protocol, ASR, capture, Backend API or interview behavior changes beyond carrying the already-tested recovery code to Windows.
- No claim that Windows is code-signed until a Windows signing certificate is available.
- No modification or retention of audio, transcript or screenshot content.

## Decisions

1. **Issue 1.1.4 instead of replacing 1.1.3 bytes.** Every rebuilt artifact receives a new patch version and immutable OSS key. Alternative: overwrite 1.1.3. Rejected because published checksums and caches would no longer identify one binary.
2. **Use the public white-background raster icon as the authoritative approved asset.** Desktop packaging and the renderer receive byte-identical or deterministically resized derivatives, and tests compare hashes/decoded pixels instead of only dimensions. Alternative: retain independent desktop art. Rejected because independent assets caused the regression.
3. **Publish three targets in one manifest operation.** The publisher receives macOS arm64, macOS x64 and Windows x64 metadata together, replacing all supported target entries only after all uploads succeed. Alternative: update platforms separately. Rejected because users can observe mixed production versions.
4. **Keep platform security state truthful.** macOS artifacts must pass Developer ID signing, App/DMG notarization, stapler and Gatekeeper. Windows remains `local-development`/not notarized until a real Windows signing certificate is available, while distribution status may remain published under the existing product policy.
5. **Verify Windows packaging on the current build host and with deterministic installer validation.** Electron cross-build output, PE architecture, installer naming, version metadata and release manifest are checked before upload. A later native Windows smoke test remains desirable but does not justify leaving production on older recovery code.

## Risks / Trade-offs

- [Windows remains unsigned] → Keep the warning and `local-development` signing state explicit; do not label it verified.
- [White-background art may render differently in small contexts] → Use the existing 1024 px approved asset and deterministic 256 px derivative, then inspect both before packaging.
- [Three large uploads can partially complete before manifest creation] → Versioned objects are harmless until the checked-in manifest is deployed; the manifest is generated only after all uploads return success.
- [Same code has platform-specific capture behavior] → Run shared Desktop tests plus Windows package validation and retain protocol 2.0 compatibility.

## Migration Plan

1. Pin the approved brand asset and add identity/version/manifest regressions.
2. Bump desktop and lockfile version to 1.1.4 and run Desktop/Web/Backend checks.
3. Build and verify notarized macOS arm64/x64 DMGs and the Windows x64 NSIS installer.
4. Upload all three artifacts and atomically generate the production manifest.
5. Commit and deploy the manifest, then verify public health, version metadata and byte-range downloads.
6. Roll back by redeploying the previous manifest; versioned 1.1.4 objects can remain inaccessible without destructive deletion.

## Open Questions

None.
