# Release 1.2.3

Release 1.2.3 is a three-platform patch for the two remaining commercial realtime blockers: slow first-visible text after entering an interview and slow visible completion after speech stops. It preserves the 1.2.2 layout, approved icon, product name, bundle identifier `com.offersteady.companion`, production endpoint defaults, and protocol 2.0 compatibility.

## Scope

- Apply peak-relative release to system audio and terminalize residual program noise from the last meaningful speech boundary instead of waiting for the hard-turn limit.
- Carry content-free last-meaningful-speech timestamps through protocol, backend aggregation, and acceptance metrics.
- Keep committing turns supervised with a three-second source watchdog and publish an immediate `transcript-committing` lifecycle event.
- Show `正在确认` in the existing transcript row after terminal admission, then transition monotonically to confirmed or incomplete.
- Send a lightweight initial session SSE snapshot before runtime diagnostics and accept a follow-up cursor-stable runtime update.
- Preserve complete-utterance replay, independent source recovery, terminal priority, explicit-only answer generation, and no transcript/audio persistence.

## Local Acceptance Gates

- Authoritative capture readiness P95 <= 2 seconds.
- Recognizable speech start to first visible partial P50 <= 1.5 seconds and P95 <= 3 seconds.
- Last meaningful speech to visible final/incomplete P95 <= 1.5 seconds and P99 <= 3 seconds.
- No unlabelled transcribing state beyond four seconds and no repeated five-second initial-snapshot fallback loop.
- Microphone and system sources pass fresh entry, residual noise, short pause, consecutive utterance, page refresh, and source recovery checks independently.
- Diagnostics contain timestamps, counters, safe IDs, and reason codes only; raw PCM and transcript text remain absent.

## Release State

Production rollout was explicitly approved after local macOS ARM64 acceptance. The shared TypeScript endpointing and protocol code is used by macOS ARM64, macOS Intel x64, and Windows x64; only the normalized PCM capture adapter differs by operating system.

## Authorized Live Evidence

- The exact local 1.2.3 ARM64 process was bound to a live production session and reported `live/capturing`.
- System audio reached 1,732 sends / 1,731 acknowledgements and microphone reached 367 sends / 365 acknowledgements at the sampled point, with zero reconnects, sequence gaps, or retransmissions.
- After computer playback stopped, system audio fell to zero send FPS with zero pending frames, confirming bounded desktop release.
- The microphone continued to admit low-rate frames during the quiet interval, so room-noise tuning remains a documented follow-up; rollout approval accepts this residual exception and does not claim Windows or Intel real-hardware latency measurements.

## Local Verification

- Protocol: 31 tests passed.
- Desktop: 147 tests passed; typecheck and production renderer/main build passed.
- Web: 304 tests passed; typecheck and guarded production build passed.
- Backend: the final rollout gate passed 337 tests with 14 skipped. An earlier local run had one load-sensitive 140 ms parallel-prewarm timing assertion measure 161 ms, then pass three isolated reruns.
- OpenSpec strict validation and JSONL eval validation passed.
- macOS arm64 bundle version: `1.2.3`; bundle identifier: `com.offersteady.companion`.
- Code signing: `Developer ID Application: Yulong li (8Y5FAR3TF3)`; deep strict verification passed.
- Approved `offersteady.icns` SHA-256 is unchanged from 1.2.2: `a81221b251a2ab7ea43177b09de529d41dc892162a1791d816286edb8c15d5d7`.
- Local ZIP SHA-256: `08c7c6017628157fe63b7f356d182fcdbd6643431c47dc0a58160a813d48e478`.

## Production Artifacts

| Target | Artifact | Bytes | SHA-256 | Verification |
| --- | --- | ---: | --- | --- |
| macOS Apple Silicon | `OfferSteady-Companion-1.2.3-macOS-arm64.dmg` | 123026577 | `dcdc14f3046594af198225641530401d0618dc1fc6884616a021c3cedfc446e4` | Developer ID verified; App/DMG notarized, stapled, and Gatekeeper accepted; main and capture runtime arm64 |
| macOS Intel | `OfferSteady-Companion-1.2.3-macOS-x64.dmg` | 126629159 | `91366082193d4883727339884e54e4967129bdef9b141ccf0b66c5686886d88f` | Developer ID verified; App/DMG notarized, stapled, and Gatekeeper accepted; main and capture runtime x86_64 |
| Windows 10/11 x64 | `OfferSteady-Companion-Setup-1.2.3-Windows-x64.exe` | 102012093 | `8ba6497fda56cdc5643cdb2510b322b9671d4806c549d3d3305baa147545be1f` | NSIS payload validated with x86-64 `OfferSteady.exe`; unsigned `local-development` status retained |

The arm64 and x64 macOS `app.asar` SHA-256 values are identical. The Windows packaged renderer SHA-256 matches the renderer used by the macOS release build, proving the endpointing/UI implementation is shared across all three artifacts; this is not a substitute for Intel or Windows real-hardware audio acceptance.

## Production Rollout

- Production source and manifest commit: `c355d4d4eee1344df104dafa692a5a65c5819d41` (`v1.2.3`).
- Pre-rollout commit: `32a2d24889f91fd77af38dd6ac2a7c9440a14186`.
- Rollback images: `offersteady-backend:rollback-32a2d24889f9-pre-1.2.3` and `offersteady-web:rollback-32a2d24889f9-pre-1.2.3`.
- The production Backend container became healthy and the Web container started successfully; public `/healthz`, `/api/v1/web/state`, and `/app` returned HTTP 200 on the first post-switch check.
- The public build manifest reports `appEnv=production` and a relative API base URL.
- The public release state reports macOS ARM64, macOS x64, and Windows x64 at 1.2.3 with the expected signing/notarization truth.
- All three public download routes returned HTTP 206 for a 1 KiB range request. Full streamed downloads reproduced the three published SHA-256 values.
- Existing clients briefly produced stale live-page heartbeat and transcript-missing retry warnings while reconnecting across the container switch; the subsequent five-minute window contained no Backend WARNING, ERROR, or CRITICAL events, and no Web error lines were observed.
