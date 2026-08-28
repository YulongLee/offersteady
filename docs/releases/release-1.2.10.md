# Release 1.2.10 Perceived Realtime Transcripts

Release 1.2.10 keeps the existing dual-channel realtime architecture and improves perceived transcript delivery. System-output turns now stop refreshing on steady residual program energy, Backend provider partial publication is isolated per session/source stripe, and Web freezes the latest visible partial at terminal admission without inferring `incomplete` from client age. Transient self-healing reconnect states remain internal while actionable permission and unrecoverable capture failures remain visible.

The companion preserves the approved layout, transparent icon family, Bundle ID, production endpoints, permission model, and protocol version.

## Verification

- Desktop: 164 tests passed across 29 files; typecheck and production build passed.
- Backend realtime receiver: 6 focused tests passed. The earlier full-suite run recorded 343 passed and 14 skipped; one unrelated load-sensitive timing assertion passed when rerun alone.
- Web release-critical suites: 58 tests passed; typecheck and guarded production build passed.
- Protocol: 31 tests passed; typecheck and build passed.
- `deliver-perceived-realtime-transcripts-1-2-10` and `hide-live-recovery-internal-status` passed strict OpenSpec validation.
- Local physical acceptance confirmed both microphone and system-output capture reached the production realtime path. Provider final confirmation could still take several seconds on the old production Backend/Web, which is the reason this release includes the server and Web rollout.

## Production Artifacts

| Target | Artifact | Bytes | SHA-256 | Verification |
| --- | --- | ---: | --- | --- |
| macOS Apple Silicon | `OfferSteady-Companion-1.2.10-macOS-arm64.dmg` | 126292325 | `199ab58e2f1a508095a896aa6ce42b6d4f2b61fca564b5a5e8edc20485ab3330` | Developer ID verified; App/DMG notarized, stapled, and Gatekeeper accepted |
| macOS Intel | `OfferSteady-Companion-1.2.10-macOS-x64.dmg` | 129836907 | `8b0c7f121a87f6bb78a9abb53f0301f0163ba81d1f092baf2fb69541cc269424` | Developer ID verified; App/DMG notarized, stapled, and Gatekeeper accepted |
| Windows 10/11 x64 | `OfferSteady-Companion-Setup-1.2.10-Windows-x64.exe` | 102148235 | `9a304effd1f35366beaa1d57aca3b9c4214c0170450c502587519e1434fd2d5d` | NSIS payload and x86-64 executable validated; existing unsigned `local-development` signing status retained |

All three versioned artifacts were uploaded before the Backend manifest changed. The Backend manifest remains the atomic website publication boundary.

## Rollback

- Retain the pre-rollout Backend and Web images with versioned rollback tags before switching application services.
- Do not recreate PostgreSQL or Redis during rollout or rollback.
- Roll back Web independently if presentation behavior regresses; roll back Backend and Web together if realtime event compatibility regresses.
- The prior 1.2.9 desktop objects remain versioned in OSS and can be restored in the manifest without deleting 1.2.10 artifacts.

## Production Rollout

- Release source and deployed application commit: `4d3a491e5b64a39183de54ded8787b0131181888`.
- Pre-rollout source: `5e660d5144f08baa0d0579fce47eb46a650ff12b`.
- Retained images: `offersteady-backend:rollback-5e660d5-pre-1.2.10` and `offersteady-web:rollback-5e660d5-pre-1.2.10`.
- Backend and Web were rebuilt serially and switched with `--no-deps`; PostgreSQL, Redis, Analytics, and Admin were not recreated.
- Backend reported `healthy` and Web reported `running` after the switch.
- Public `/healthz`, `/app`, `/api/v1/web/state`, and `/api/v1/realtime-speech/status` returned HTTP 200.
- The public Web build manifest reported `appEnv=production` and `apiBaseUrl=/`.
- The public download manifest exposed macOS arm64, macOS x64, and Windows x64 at version 1.2.10. Each download endpoint returned HTTP 206 for a one-byte range with the expected total size and content type.
