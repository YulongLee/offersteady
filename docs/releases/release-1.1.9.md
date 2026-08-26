# Release 1.1.9

Release 1.1.9 separates the macOS permission and local-runtime-identity repair from the 1.1.8 headset/transport recovery baseline. It preserves bundle identifier `com.offersteady.companion`, the approved product icon, realtime protocol `2.0`, and the 1.1.8 rollback artifact.

## Fixes

- Pins every launch method to the stable `@offersteady/desktop` user-data directory before Electron sessions and stores initialize.
- Migrates only a missing legacy pairing identity, encrypted device credential, and screenshot shortcut; existing stable identity always wins.
- Does not copy Chromium caches, diagnostics, screenshots, transcripts, media, or raw audio during migration.
- Gates macOS display-source acquisition on the Screen & System Audio Recording permission instead of repeatedly calling Electron while permission is denied.
- Contains display-source failures as a typed unavailable result and prevents an unhandled rejection from terminating or destabilizing the companion.
- Keeps microphone capture independent when computer-output permission is unavailable and shows a direct permission-settings action with restart guidance.

## Acceptance boundary

- Local automated verification, packaging, installation, and physical Mac acceptance are recorded in the associated OpenSpec tasks.
- 1.1.9 is not considered production-published until the installed signed app reports the stable pairing identity, system-audio frames receive Backend acknowledgements, and the headset transition test completes.
- Rollback uses the retained 1.1.8 package and does not delete either local data directory.

## Local acceptance artifact

| Target | Artifact | SHA-256 | Signing |
| --- | --- | --- | --- |
| macOS Apple Silicon | `OfferSteady-Companion-1.1.9-macOS-arm64.zip` | `dd42164b5ba91b09030d43d61d4c901a22213c40cc3498deacad88a531215253` | Developer ID identity `8Y5FAR3TF3`; local acceptance ZIP, not reported as notarized production distribution |

Automated acceptance passed 28 Desktop test files / 140 tests, Desktop type checking, main/renderer builds, package signature verification, and strict OpenSpec validation. Physical system-audio permission and headset-transition acceptance remains pending user consent on the installed Mac.

## Privacy and security

The change does not add audio, transcript, screenshot, or personal-data persistence. Migration is limited to local device identity metadata, an encrypted credential when present, and the user's screenshot-shortcut setting. API keys and credentials are neither logged nor printed.
