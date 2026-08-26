# Release 1.1.4

Release 1.1.4 completes the cross-platform rollout of the realtime publisher recovery correction and restores the approved white-background companion icon. It preserves bundle identifier `com.offersteady.companion` and realtime protocol `2.0`.

## Corrections

- Ships the same recovery implementation on macOS Apple Silicon, macOS Intel and Windows x64.
- Replaces the stale dark-background desktop icon in both the packaged application and the companion window.
- Pins packaging and renderer icon identities with deterministic SHA-256 regressions.
- Keeps Windows signing state truthful until an Authenticode certificate is available.

## Verification

- Desktop: 110 tests passed, type checks passed and production build passed.
- OpenSpec strict validation and diff checks passed.
- Both macOS apps and DMGs passed Developer ID signing, notarization, stapler and Gatekeeper checks.
- Both packaged macOS icon containers rendered the approved white-background icon and matched each other.
- Windows NSIS validation confirmed the 1.1.4 installer and packaged `OfferSteady.exe`; metadata remains `local-development`, `notarized: false`.

## Production artifacts

| Target | Artifact | SHA-256 | Security state |
| --- | --- | --- | --- |
| macOS Apple Silicon | `OfferSteady-Companion-1.1.4-macOS-arm64.dmg` | `c79ac6e8e849cbfe5afbabd1943037deb269bd4b817991e07494054e1d1b0a49` | Developer ID verified; App/DMG notarized and stapled |
| macOS Intel | `OfferSteady-Companion-1.1.4-macOS-x64.dmg` | `310e9551177aa337b3e8a65f24136115ab197f077a4590443e7c139acf576bc0` | Developer ID verified; App/DMG notarized and stapled |
| Windows x64 | `OfferSteady-Companion-Setup-1.1.4-Windows-x64.exe` | `8c7d402c1aaee639a32f86d7fe5850aa812aadb2533fd686fc8dbba0ddd23c18` | Unsigned; explicitly reported as `local-development` |

All three artifacts were uploaded under immutable 1.1.4 OSS object keys in one publication run, and the generated production manifest contains exactly the three aligned targets.

The production manifest was deployed on 2026-08-26 with Backend health passing. The public state API reported all three targets at 1.1.4 with protocol 2.0, both macOS entries verified/notarized, and Windows explicitly `local-development`/not notarized. Byte-range probes for all three public download routes returned HTTP 206.
