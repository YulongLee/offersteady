# Global Companion 1.2.17

- Released: 2026-09-06
- Global host: `47.84.65.103`
- Release path: `/opt/offersteady-global/releases/20260906-global-companion-1217`
- Public product: `https://offersteady.com`

## Fix

The 1.2.16 Global package rendered the English UI but its Electron main process could identify itself as the domestic edition during early startup. It therefore used the domestic user-data directory and domestic API. Version 1.2.17 resolves the edition from the immutable Global runtime resource embedded in the packaged artifact, preserving the explicit environment override for development builds.

## Artifacts

| Platform | File | SHA-256 | Trust status |
| --- | --- | --- | --- |
| macOS Apple Silicon | `OfferSteady-Companion-Global-1.2.17-macOS-arm64.dmg` | `f59db0ad9dad3ee0021505c36f53c998a6042100946a61dccdb0baea2a69c46b` | Developer ID signed, Apple notarized and stapled |
| macOS Intel | `OfferSteady-Companion-Global-1.2.17-macOS-x64.dmg` | `69d09fcf1d0960bbc92b5590073a6d5130f98247ec51d86c59ae117a033e9abe` | Developer ID signed, Apple notarized and stapled |
| Windows x64 | `OfferSteady-Companion-Global-Setup-1.2.17-Windows-x64.exe` | `16c832112c5c477f15455595bdf442d206c159ea2d0d451b1a51347efe91f680` | Unsigned; Windows commercial code-signing certificate remains pending |

## Verification

- Desktop tests: 196 passed.
- Desktop TypeScript checks: passed.
- OpenSpec strict validation: passed.
- Packaged macOS arm64 runtime used `@offersteady/desktop/global` and connected to `47.84.65.103:443`.
- The overseas pairing endpoint recorded the launched package as a registered Global device.
- Both macOS DMGs passed code-sign verification, Apple notarization, stapler validation, and Gatekeeper assessment.
- Public `/api/v1/web/state` returned version `1.2.17` for macOS arm64, macOS x64, and Windows x64.
- All three public download flows returned HTTP 200 from object storage with the expected content length.
- The overseas backend remained healthy; Web, PostgreSQL, Redis, analytics, and admin services were not restarted.

## Rollback

The previous backend image is retained as `offersteady-global-backend:rollback-20260906-before-companion-1217`. The preceding release remains `/opt/offersteady-global/releases/20260906-global-companion-1216`. No database migration was included.
