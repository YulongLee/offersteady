# Release 1.2.1

Release 1.2.1 is a transport-recovery patch for companion 1.2.0. It preserves bundle identifier `com.offersteady.companion`, the approved product icon, renderer layout and styles, interview workflow, and realtime protocol `2.0`.

## Included fixes

- Keeps transient publisher reconstruction in a single-flight, bounded-backoff recovery loop instead of becoming permanently disconnected after a small retry budget is exhausted.
- Resumes both authoritative sequence offsets and source generations when the Desktop process reconnects to the same live interview.
- Prevents the `stale-source-generation` and `sequence-gap` loop that could make a restarted companion appear connected while new speech received no acknowledgement.
- Keeps microphone and system-output recovery independent and retains explicit terminal authorization failures.

## UI and application identity

This patch does not change the 1.2.0 layout, styles, icon, product name, Bundle ID, or interview workflow. Electron development-window chrome is not part of the packaged production UI.

The macOS release uses the same Developer ID application identity and `com.offersteady.companion` Bundle ID. That stable identity allows macOS to reuse an existing microphone or screen/system-audio grant when its privacy service permits. Apple developer-account access does not bypass macOS privacy controls; if TCC requires authorization, the user must grant it in System Settings.

## Verification and privacy

Automated verification uses synthetic frames and metadata-only counters. It does not store or publish interview audio, transcript text, screenshots, credentials, or personal information.

## Local release artifacts

Artifact hashes and trust results are recorded here after local packaging. Production publication and deployment are intentionally unchanged until separately authorized.

| Target | Artifact | Size (bytes) | SHA-256 | Trust state |
| --- | --- | ---: | --- | --- |
| macOS Apple Silicon | `OfferSteady-Companion-1.2.1-macOS-arm64.dmg` | 123035215 | `38911444a89369b0daa22b7743618a45a9dbd12e18c4a54a0e351a72b27d59cd` | Developer ID verified, notarized, stapled, Gatekeeper accepted |
| macOS Intel | `OfferSteady-Companion-1.2.1-macOS-x64.dmg` | 126625201 | `0cf6c3e89ba5cfd54e78973007fc6da6e16c872a9bb4eef9bd79cdf3bb5b9d38` | Developer ID verified, notarized, stapled, Gatekeeper accepted |
| Windows 10/11 x64 | `OfferSteady-Companion-Setup-1.2.1-Windows-x64.exe` | 102011907 | `047f12617bfb3f10defadebe7392747bdef333cc07c2e0ade077479ee208b073` | Structurally validated; unsigned / `local-development` signing status |

## Rollback

The immutable 1.2.0 packages remain available. A local rollback reinstalls 1.2.0; any later backend rollout remains independently recoverable to its prior deployment.

The production pre-rollout source and manifest are commit `b505418508f014e67919b5a87407bbb9f5a9a3c2`. The running Backend image was retained before rollout as `offersteady-backend:rollback-b505418-pre-1.2.1` with image ID `sha256:c711f02944be44548f75501e4c27028b6989af4b77080c47516689809267bb74`. PostgreSQL, Redis, and Web are outside this release deployment scope.
