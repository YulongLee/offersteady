## Why

Production validation shows that removing or switching a headset on macOS can recreate the shared desktop publisher, reset channel sequences, trigger a resend storm, and stop both microphone and system-audio upload. A commercial interview session must survive normal audio-route changes without requiring the user to leave and re-enter the interview.

## What Changes

- Treat macOS audio-device changes as a debounced source transition instead of immediately recreating the whole dual-channel publisher.
- Keep microphone and system-audio recovery isolated so a failed input route does not stop the healthy channel.
- Make publisher replacement sequence-safe, bound retransmission, and accept silence during recovery without exhausting the replacement budget.
- Surface a temporary device-switching state and automatically return to capture when the replacement source becomes healthy.
- Add synthetic regressions for headset removal, repeated `devicechange`, silent replacement sources, sequence reset, and resend amplification.
- Increment the desktop companion patch version from 1.1.5 to 1.1.6 and publish verified macOS and Windows artifacts.

## Capabilities

### New Capabilities

- `resilient-audio-device-hot-switch`: Defines bounded, channel-isolated desktop audio recovery and sequence-safe transport behavior when an operating-system audio route changes.

### Modified Capabilities

None.

## Impact

- Desktop device discovery, active capture lifecycle, microphone/system source recovery, shared WebSocket transport, diagnostics, and release metadata under `apps/desktop`.
- Backend protocol compatibility may receive a narrowly scoped publisher-generation correction only if regression evidence proves it is required.
- No persistence of PCM or transcript content, no new client secrets, and no change to answer or billing behavior.
