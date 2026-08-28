# Release 1.2.7 Commercial Audio Boundary Hardening

Release 1.2.7 hardens the realtime interview boundary as one compatible Desktop, Backend, and Web change. It reduces ambient-noise false starts, carries privacy-safe preparation calibration into live capture, and bounds provider-final recovery while preserving the latest visible partial.

## Included

- Source-specific calibrated admission with sustained activity and bounded pre-speech retention.
- Strong microphone speech admission after about 100 milliseconds; calibrated quiet paths remain bounded below 400 milliseconds in deterministic fixtures.
- Preparation-to-live transfer of the media handle plus noise floor/sample-count metadata; no preparation PCM is transferred or published.
- Explicit production manual commit, a two-second provider completion budget, and a 2.5-second source watchdog.
- Production Web three-step readiness gate and monotonic `final`/`incomplete` presentation.
- Content-free stage diagnostics only; no PCM, transcript text, API keys, or personal material enters diagnostics.

## Compatibility

- Bundle identifier: `com.offersteady.companion`.
- Protocol: existing optional-field-compatible realtime protocol.
- Layout/icon: approved 1.2.4 visual surface and transparent icon family are unchanged.
- Default production endpoint remains `https://mianshiwen.cn`.

## Rollback

Backend, Web, and companion are backed up independently before promotion. No database migration is required. Restoring the previous application and production images returns the prior behavior without deleting user data.

## Acceptance Boundary

Automated builds cover supported package targets, but this release cycle physically opens and validates only the Apple Silicon package. Intel macOS and Windows require separate hardware acceptance before equal physical evidence can be claimed.
