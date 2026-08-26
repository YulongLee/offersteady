# Release 1.1.3

Release 1.1.3 is the production patch for truthful realtime publisher recovery. It preserves bundle identifier `com.offersteady.companion` and realtime protocol `2.0`.

## Fixes

- Separates replacement WebSocket readiness from first-media acknowledgement so normal silence cannot create Publisher churn.
- Starts the bounded ACK deadline only after replacement media is produced or queued.
- Resets source sequencing for the replacement Publisher and ignores acknowledgements from superseded transports.
- Removes the disabled legacy HTTP frame fallback from the desktop production publisher.
- Makes exhausted recovery a sticky terminal delivery failure with explicit reconnect guidance.
- Bounds the initial Web realtime snapshot to authoritative current state and the latest required stateful events.
- Preserves immediate non-final partial subtitles and monotonic in-place revision replacement.

## Local verification

The final Apple Silicon local application was built with SHA-256 `21e6d2538cfbcace646e1ce34fcf8b7c5b28159e54acbf4ca3c18b8c15c00291`. Version `1.1.3`, bundle identifier `com.offersteady.companion`, and strict local code-signature verification passed. The installed 1.1.2 application and the pre-offset-fix 1.1.3 application were moved to recoverable test backups before the corrected 1.1.3 build was installed and launched.

Full verification passed: 558 Node/Vitest tests, 326 Backend tests with 14 environment-dependent skips, all workspace type checks, production Desktop/Web builds, and strict OpenSpec validation.

The controlled production-connected system-audio run completed on the locally installed 1.1.3 application without retaining audio or transcript content. Across the final continuous sample, capture and publisher input advanced together to 18,722 frames, the WebSocket sent 3,139 unique frames and received 3,139 authoritative acknowledgements through sequence 3,138. Publisher reconnects, repeated sequence sends, sequence gaps and resend frames all remained zero; the final ring buffer and retransmit queue depths were zero. This verifies one active publisher, no false-online upload state and sustained forward progress for the tested path. Subtitle wording and interview content were deliberately excluded from the diagnostic record.

## Production artifacts

| Target | Artifact | SHA-256 | Verification |
| --- | --- | --- | --- |
| macOS Apple Silicon | `OfferSteady-Companion-1.1.3-macOS-arm64.dmg` | `a1721b2f187feac6ea07e4f31c1b3542be00716f87b320effce414fb558ae3c3` | Developer ID, App/DMG notarization, stapler and Gatekeeper passed |
| macOS Intel | `OfferSteady-Companion-1.1.3-macOS-x64.dmg` | `eb4e9e4142a5d9c0c7826d6be12b91d2b61465dd2d335cf553a1a6d309ea942b` | Developer ID, App/DMG notarization, stapler and Gatekeeper passed |

Both artifacts were uploaded to versioned production OSS paths. The production manifest updates both macOS architectures atomically and retains the existing Windows 1.1.2 entry.

Backend/Web compatibility changes and the production download manifest were deployed on 2026-08-26. Public health passed, both macOS 1.1.3 download routes returned their production objects, and byte-range probes returned HTTP 206. The server repository and deployment marker matched manifest commit `9f71071` during rollout verification.
