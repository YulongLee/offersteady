# Release 1.1.1

Release 1.1.1 is the commercial realtime audio transport hotfix for the 1.1 desktop line. It preserves bundle identifier `com.offersteady.companion` and realtime protocol `2.0`.

## Fixes

- Bounds each logical audio channel to eight unacknowledged WebSocket frames.
- Resends only the exact Backend-requested sequence and suppresses repeated gap responses.
- Reconciles Backend resume offsets before flushing queued audio.
- Recreates both enabled capture sources and resets sequencing when continuity is impossible.
- Closes defective Backend ingress connections after eight sequence gaps without progress.
- Requires a fresh frame acknowledgement before recovered delivery is reported healthy.

## Verified artifacts

| Target | Artifact | SHA-256 | Integrity |
| --- | --- | --- | --- |
| macOS Apple Silicon | `OfferSteady-Companion-1.1.1-macOS-arm64.dmg` | `40e8c71c500af493780941832c45153f037edc52258be4c14e0c8fd5399cf2a0` | Developer ID, App/DMG notarization, stapler and Gatekeeper passed |
| macOS Intel | `OfferSteady-Companion-1.1.1-macOS-x64.dmg` | `1fa03520db74dec5a18dd1ad5b7653c549effef0a9130bf6788df28a23b2a86b` | Developer ID, App/DMG notarization, stapler and Gatekeeper passed |
| Windows x64 | `OfferSteady-Companion-Setup-1.1.1-Windows-x64.exe` | `eab6185876447347b3ea184ec4f19a61b16be43e240482aba8aabc8535a899f6` | NSIS structure passed; Authenticode remains unavailable |

The Backend is deployed before the new desktop manifest is published. Public health, checksums and a controlled live frame ACK are verified after rollout.
