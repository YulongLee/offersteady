# Release 1.1.3

Release 1.1.3 is the local verification build for truthful realtime publisher recovery. It preserves bundle identifier `com.offersteady.companion` and realtime protocol `2.0`. It is not published in the production download manifest.

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

Full verification passed: 558 Node/Vitest tests, 326 Backend tests with 14 environment-dependent skips, all workspace type checks, production Desktop/Web builds, and strict OpenSpec validation. Production Backend, Web, signed release artifacts and the public download manifest remain unchanged during this step.

The controlled production-connected system-audio run completed on the locally installed 1.1.3 application without retaining audio or transcript content. Across the final continuous sample, capture and publisher input advanced together to 18,722 frames, the WebSocket sent 3,139 unique frames and received 3,139 authoritative acknowledgements through sequence 3,138. Publisher reconnects, repeated sequence sends, sequence gaps and resend frames all remained zero; the final ring buffer and retransmit queue depths were zero. This verifies one active publisher, no false-online upload state and sustained forward progress for the tested path. Subtitle wording and interview content were deliberately excluded from the diagnostic record.
