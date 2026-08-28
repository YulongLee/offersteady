# Release 1.2.9 Background Realtime Activation

Release 1.2.9 disables Electron background throttling for the companion renderer. The companion normally loses focus when the user enters the interview browser; realtime binding control polls and audio callbacks must continue at their configured cadence in that state.

It also pins a healthy live publisher to its authoritative session binding. A newer unrelated binding cannot silently replace an active live interview, and initial publisher startup no longer presents itself as an audio-gap reconnect. Real recovery after an established transport failure remains visible.

The preparation waiting poll remains 250 milliseconds. This release does not change VAD thresholds, endpointing, provider model behavior, UI layout, icons, or privacy boundaries.

## Acceptance

- With the companion behind the interview browser, a successful live start is observed without the prior one-second renderer clamp.
- Prepared audio sources are promoted without reopening healthy devices.
- No preparation PCM is published.
- A second account cannot take over a device serving a live interview.
- Initial publisher startup remains non-alarming; a real post-healthy transport recovery still reports `reconnecting`.
