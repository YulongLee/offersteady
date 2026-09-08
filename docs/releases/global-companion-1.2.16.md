# Global Companion 1.2.16

- Released: 2026-09-06
- Global host: `47.84.65.103`
- Release path: `/opt/offersteady-global/releases/20260906-global-companion-1216`
- Public product: `https://offersteady.com`

## Artifacts

| Platform | File | SHA-256 | Trust status |
| --- | --- | --- | --- |
| macOS Apple Silicon | `OfferSteady-Companion-Global-1.2.16-macOS-arm64.dmg` | `6b26fe008b12d16fb3ae892dda828ba136b37ba36678ddaf70915bd71f3f6d15` | Developer ID signed, Apple notarized and stapled |
| macOS Intel | `OfferSteady-Companion-Global-1.2.16-macOS-x64.dmg` | `d528c9b03c3311d8bc1e75eb378f59fd11f08f7e35a7522a072f907ffc5ac673` | Developer ID signed, Apple notarized and stapled |
| Windows x64 | `OfferSteady-Companion-Global-Setup-1.2.16-Windows-x64.exe` | `19b91e90bb4349a7166127079f606a1ae5659176d15ac0cd172195417e126d3b` | Unsigned; Windows commercial code-signing certificate remains pending |

All artifacts use the isolated Global identity, release channel, `https://offersteady.com` Web target, and `https://offersteady.com/api/v1` API target. Objects are stored below the isolated `global-desktop-releases/` prefix.

## Verification

- Desktop tests: 193 passed.
- Desktop TypeScript checks: passed.
- Backend publication and product-edition tests: 8 passed.
- OpenSpec strict validation: passed.
- Both macOS DMGs passed code-sign verification, image verification, Apple notarization, stapler validation, and Gatekeeper assessment.
- Public `/api/v1/web/state` returned version `1.2.16` for macOS arm64, macOS x64, and Windows x64.
- Each public download endpoint resolved successfully to the uploaded object.
- Global backend remained healthy after the isolated backend replacement; no new backend error markers were found.

## Rollback

The previous backend image is retained as `offersteady-global-backend:rollback-20260906-before-companion-1216`. The preceding release directory remains `/opt/offersteady-global/releases/20260905-global-auth-purpose-fix-2`. No database migration was included.
