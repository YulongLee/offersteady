## Why

Production validation on companion 1.1.6 reproduced a live-audio deadlock: capture callbacks continued while microphone upload stopped after 16 unique frames and system upload later stopped after 83, leaving both eight-frame send windows blocked and subtitles delayed or absent. The previous hot-switch release treated shared-transport recovery as complete after any channel acknowledgement and did not guarantee recovery from a clean-but-unexpected WebSocket close, so commercial interviews can still appear healthy while no audio reaches ASR.

## What Changes

- Make realtime delivery health and recovery acknowledgement channel-specific; one healthy channel must not hide another channel whose frames are unacknowledged.
- Recover the shared transport from every unexpected close, including code 1000 when the desktop did not intentionally stop it.
- Detect a full in-flight window with no forward ACK progress and replace the transport through one bounded, single-flight recovery path.
- Reconcile resume offsets, queued frames, send buffers, and sequencers atomically so replacement publishers cannot retain stale frames or regress channel sequence ownership.
- Keep microphone and system capture isolated during device changes while ensuring both channels independently prove fresh media progress after transport replacement.
- Add deterministic regressions matching the production counters, long-running dual-channel soak tests, and metadata-only diagnostics that expose transport generation and per-channel forward progress.
- Increment the companion patch release from 1.1.6 to 1.1.7 and verify macOS arm64/x64 plus Windows x64 artifacts before production publication.
- Do not persist PCM, transcript content, API keys, publisher tokens, or user content in diagnostics or fixtures.

## Capabilities

### New Capabilities

- `deadlock-free-dual-channel-audio-delivery`: Defines per-channel ACK health, bounded shared-transport recovery, atomic sequence reconciliation, unexpected-close handling, and verifiable companion 1.1.7 behavior.

### Modified Capabilities

None.

## Impact

- Desktop realtime transport, reliability watchdog, publisher recovery gate, bounded buffers, diagnostics, tests, and release metadata under `apps/desktop`.
- Backend WebSocket connection-state and acknowledgement compatibility tests under `apps/backend`; protocol 2.0 remains compatible unless evidence requires an additive metadata field.
- Production companion manifests and signed/notarized artifacts for macOS and Windows.
- No prompt, answer, billing, ASR model, transcript persistence, or raw-audio retention changes.
