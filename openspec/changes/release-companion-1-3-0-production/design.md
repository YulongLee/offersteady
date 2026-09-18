# Design: Companion 1.3.0 production publication

## Release targets

Each edition publishes six artifacts:

| Edition | macOS arm64 | macOS x64 | Windows x64 |
| --- | --- | --- | --- |
| Domestic | Developer ID signed + notarized DMG | Developer ID signed + notarized DMG | PE/NSIS installer, unsigned and explicitly labeled |
| Global | Developer ID signed + notarized DMG | Developer ID signed + notarized DMG | PE/NSIS installer, unsigned and explicitly labeled |

The domestic artifacts use the normal production endpoint and `com.offersteady.companion`. Global artifacts embed the isolated Global runtime configuration and use `com.offersteady.companion.global`.

## Publication flow

1. Run desktop tests, typecheck, and renderer/main builds from the current 1.3.0 source.
2. Build domestic macOS DMGs through the fail-closed production wrapper with the existing Apple keychain profile; generate and verify production metadata.
3. Build Global macOS DMGs with the Global runtime configuration, Developer ID identity, manual notarization/stapling, and the Global metadata generator.
4. Build domestic and Global Windows x64 NSIS installers, validate PE structure and packaged executable, and generate metadata with unsigned status.
5. Upload immutable artifacts under the existing domestic and Global OSS prefixes.
6. Update each backend release manifest only after all three artifacts for that edition upload successfully.
7. Deploy the manifest/backend release change through the existing production deployment path, without restarting unrelated services.

## Safety and rollback

- Keep existing 1.2.x OSS objects and manifest entries available until the new public state and download probes pass.
- Do not replace a backend service while a realtime interview is active; the artifact upload itself does not interrupt running interviews.
- A failed signing, notarization, hash, upload, or public probe stops the release before the corresponding edition manifest is switched.
- Rollback is restoring the prior manifest and retaining the new immutable objects for investigation.
