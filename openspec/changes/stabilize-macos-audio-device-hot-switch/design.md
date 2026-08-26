## Context

The production companion owns microphone and system-output capture in one Electron renderer and multiplexes both logical channels over one WebSocket. During the observed macOS headset removal, capture was initially healthy with zero gaps and complete acknowledgements. The operating-system `devicechange` then caused React device-selection state to recreate the entire `DesktopRealtimePublisher` several times. A repeated sequence-gap response also cleared all in-flight markers before its cooldown check, allowing eight unique system frames to amplify into hundreds of sends. Replacement attempts eventually exhausted and stopped both channels.

The current UI refreshes the device list on every raw `devicechange`, prefers the current default device before an explicitly selected device, and includes the selected microphone in the whole-publisher effect dependencies. Source-level recovery exists, but UI-driven selection changes bypass it. Raw audio must remain memory-only and diagnostics must remain metadata-only.

## Goals / Non-Goals

**Goals:**

- Keep the publisher WebSocket and healthy channel alive across a macOS headset or default-route change.
- Debounce noisy device notifications and reconcile selection without oscillating between equivalent default-device identities.
- Switch only the affected microphone source on an existing publisher while preserving channel sequence continuity.
- Bound repeated sequence-gap handling so duplicate server responses cannot amplify a small queue into a resend storm.
- Recover automatically or leave only the unavailable source degraded, with clear user-visible state.
- Ship the companion fix as patch version 1.1.6 for supported macOS and Windows packages.

**Non-Goals:**

- Replace Electron capture, ScreenCaptureKit, Qwen ASR, or WebSocket protocol 2.0.
- Persist audio, transcript content, tokens, or credentials in diagnostics.
- Promise seamless Bluetooth hardware reconnection when macOS exposes no replacement device; the healthy channel and session must still survive.
- Change answer generation, billing, or transcript semantics.

## Decisions

### Separate device selection from publisher ownership

Raw `devicechange` notifications will be debounced. Device reconciliation will retain the selected device while it remains available; if it disappears, it will fall back to the logical default and emit one stable selection change. The React publisher lifecycle will no longer depend on microphone selection, so changing a headset cannot destroy the shared WebSocket or system channel.

Recreating the whole publisher after a device notification was rejected because macOS can emit several notifications for one physical action and because it unnecessarily resets both channels.

### Add a serialized microphone source switch on the existing publisher

`DesktopRealtimePublisher` will expose an idempotent microphone-selection update. It will remember the latest desired device, serialize transitions, stop only the current microphone runtime, reopen the latest desired route, and leave the system runtime and transport untouched. If a second notification arrives during recovery, the loop converges on the newest desired device instead of dropping it.

Using the existing whole-publisher React effect with a debounce was rejected because even one legitimate device change would still reset system capture and the shared transport.

### Preserve channel sequence and terminal boundaries during a source switch

A source switch continues the existing microphone sequence namespace on the same publisher. Stopping the old runtime flushes any terminal boundary before the new runtime starts. Old runtime callbacks are detached before the replacement becomes active, and the source-recovery lock prevents overlapping writers.

Resetting the microphone sequence was rejected because the backend receipt for the active publisher remains authoritative and would report a gap.

### Apply gap cooldown before mutating in-flight state

Repeated gap responses for the same expected sequence inside the cooldown window will be ignored before clearing sent markers. Only a permitted bounded retry can clear and resend the expected frame. When the retry budget is exhausted or the expected frame is unavailable, transport replacement remains the terminal recovery path.

Increasing buffers or retry counts was rejected because it would amplify traffic and delay failure without restoring correctness.

### Treat silence as healthy after control-plane recovery

A replacement transport is considered control-plane ready after its connection-state and authoritative resume offsets arrive. The first media frame still has a bounded acknowledgement deadline once media exists, but a silent source does not consume publisher attempts merely because no frame was produced.

## Risks / Trade-offs

- [macOS emits several device identities for one route] → Debounce notifications and prefer the still-available selection before falling back to the logical default.
- [A switch arrives while another source recovery is running] → Store the latest desired microphone ID and serialize until the active input converges.
- [Stopping an old runtime emits a terminal frame during the switch] → Preserve the existing sequence and terminal acknowledgement path before opening the replacement.
- [A truly broken shared WebSocket could be mistaken for a source-only issue] → Keep the independent transport watchdog and bounded publisher replacement for missing frame acknowledgements.
- [Windows device notifications differ from macOS] → Keep the logic platform-neutral and run Windows packaging regressions, while the production incident acceptance remains macOS-specific.

## Migration Plan

1. Add synthetic selection, source-switch, repeated-gap, silence, and channel-isolation regressions.
2. Implement debounced selection reconciliation, publisher-stable microphone switching, and bounded gap retry behavior.
3. Increment desktop release metadata to 1.1.6 and run focused plus full workspace verification.
4. Build and verify macOS arm64/x64 and Windows x64 artifacts with immutable checksums.
5. Publish the companion manifest without changing Web or Backend unless compatibility tests demonstrate a server correction is necessary.
6. Verify production health and metadata-only transport behavior, then ask the user to repeat a consented headset-removal acceptance test.

Rollback restores the 1.1.5 desktop manifest; Web and Backend remain independently deployable.

## Open Questions

None.
