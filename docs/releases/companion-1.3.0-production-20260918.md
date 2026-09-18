# OfferSteady Companion 1.3.0 production release

Date: 2026-09-18 (Asia/Shanghai)

This release publishes Companion 1.3.0 for both the domestic and Global editions. The backend, interview, ASR, billing, database, Redis, and web behavior were not changed; only the desktop release manifests and the backend images that serve those manifests were updated.

## Verification before publication

- Desktop test suite: 36 files, 198 tests passed.
- Desktop TypeScript typecheck: passed.
- Desktop production build: passed.
- macOS arm64/x64 DMGs: Developer ID signed, notarized with the existing keychain profile, stapled, Gatekeeper assessed, and stapler-validated.
- Windows x64 installers: PE/NSIS package validation passed. Windows remains unsigned under the current distribution policy.

## Published artifacts

| Edition | Platform | Size (bytes) | SHA-256 | Trust state |
| --- | --- | ---: | --- | --- |
| Domestic | macOS arm64 | 126269016 | `ff147e79d48367484c3df49ffc991b83754cae100eb1fa11f3a6f2ed396546e0` | verified, notarized |
| Domestic | macOS x64 | 129836915 | `620dbe599298a4d9df0ee5c510120ab4ba5bd54e120068c18a421d0fff2f3889` | verified, notarized |
| Domestic | Windows x64 | 102152122 | `5c384e3abf45b43d72787c33ff15c82c760a7537108c040e2557a3b638cebe3b` | unsigned |
| Global | macOS arm64 | 126701308 | `a7dd8eafc95224f001708cc072a34c4e5af6c63df5d029769450efa74c913074` | verified, notarized |
| Global | macOS x64 | 130376074 | `a37febd0be85684f98369978d46321c625dc6e4ed1d315565fd2ab101a645654` | verified, notarized |
| Global | Windows x64 | 102797617 | `a2ad5e5a4fa79dac92c311363409819757a0e6538aceddf33c75ea57185c8fad` | unsigned |

Artifacts are stored under immutable 1.3.0 OSS keys. Previous release objects were not deleted.

## Online deployment

- Domestic OSS prefix: `desktop-releases/{platform}/{architecture}/1.3.0/`.
- Global OSS prefix: `global-desktop-releases/{platform}/{architecture}/1.3.0/`.
- Domestic backend manifest was backed up at `/opt/offersteady/rollback/desktop_release_manifest-20260918-190158.json` before the backend image was rebuilt and the backend container recreated.
- Global backend manifest was backed up at `/opt/offersteady-global/rollback/global_desktop_release_manifest-20260918-190404.json` before the backend image was rebuilt and the backend container recreated.
- Database, Redis, web, worker, analytics, and admin containers were not restarted.

## Public verification after deployment

- `https://mianshiwen.cn/healthz`: HTTP 200; backend healthy.
- `https://offersteady.com/healthz`: HTTP 200; backend healthy.
- Both public `web/state` responses report version `1.3.0` for macOS arm64, macOS x64, and Windows x64.
- All six public download routes returned HTTP 206 for a byte-range probe and reported the expected artifact size.
- Existing installed assistants are not force-upgraded by this release; users receive 1.3.0 through the normal download/update flow.

## Rollback

Restore the corresponding backed-up manifest, rebuild only that edition's backend image, and recreate only its backend service. The immutable 1.3.0 OSS objects remain available for re-verification.
