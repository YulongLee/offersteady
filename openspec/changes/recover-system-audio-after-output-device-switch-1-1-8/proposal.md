## Why

Removing a headset on macOS can end both the ScreenCaptureKit loopback track and the headset microphone track. The current one-shot recovery destroys the old runtime, then leaves capture permanently stopped if the replacement open races the operating-system route transition or continues targeting the removed microphone ID.

## What Changes

- Add a persistent, bounded system-audio recovery supervisor that retries after output-device transitions without recreating the shared publisher.
- Preserve the system channel sequence and terminal boundary across recovery; prevent diagnostic sequence regression during resends.
- Keep microphone capture and the interview session alive when system capture is temporarily unavailable.
- Fall back to the operating-system default microphone with bounded retries when the selected headset input disappears.
- Add synthetic headset-removal/open-failure/recovery regressions and metadata-only diagnostics.
- Keep an unacknowledged terminal across transport resume offsets and re-admit it server-side until `terminal-accepted` closes the turn.
- Increment and publish the desktop companion patch version from 1.1.7 to 1.1.8 after verification.

## Capabilities

### New Capabilities

- `durable-system-audio-hot-recovery`: Bounded retry, channel isolation, sequence continuity, and production acceptance for macOS output-route changes.

### Modified Capabilities

None.

## Impact

- Affects Desktop microphone/system-audio capture lifecycle, transport recovery, Backend terminal admission, diagnostics, tests, and release metadata.
- Does not change Backend protocol 2.0, ASR models, transcript semantics, billing, or raw-audio persistence.
