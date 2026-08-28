## Why

The 1.2.6 acceptance session proves that capture and WebSocket delivery can remain healthy while the user still sees three commercial blockers: ambient noise can create transcript text, quiet system speech can remain locally gated for tens of seconds, and a stopped utterance can remain unfinished for several seconds. These boundaries must be solved together because globally raising or lowering one RMS threshold trades false positives for missed first speech.

## What Changes

- Add calibrated, source-specific speech admission that combines a bounded noise baseline, sustained activity, hysteresis, and pre-speech retention instead of accepting a single low RMS transition.
- Carry privacy-safe calibration/readiness evidence across preparation-to-live warm handoff so entering live mode does not cold-start source detection or reopen verified devices.
- Expose content-free speech-boundary diagnostics that distinguish capture, local admission, terminal enqueue/ACK, provider completion, recovery, and browser terminal presentation.
- Make preparation automatic: binding the companion opens/calibrates local sources and prewarms both provider channels without requiring the user to produce test sound.
- Bound the preparation-to-live control transition so the companion observes start promptly and promotes the already-open sources without a cold device/provider start.
- Bound visible terminalization: emit the desktop terminal promptly, keep the latest provider partial visible, and move a provider-stalled turn to an explicit recoverable terminal state instead of leaving it indefinitely active.
- Pin the companion to its active live binding until the Backend authoritatively releases it, and reject another account silently taking over a device that is already serving a live interview.
- Reserve the global `reconnecting` state for a previously established transport that is actually recovering; initial publisher startup and temporarily absent per-source health SHALL remain non-alarming.
- Deploy the compatible Backend and Web readiness/finalization behavior before installing the signed Apple Silicon companion 1.2.7; preserve the current production release as an independently restorable rollback.
- Non-goals: storing preparation/live PCM, preparation transcription or billing, changing the ASR model or answer prompts, redesigning the approved companion/live layout, or claiming Intel macOS/Windows physical acceptance from this Apple Silicon cycle.

## Capabilities

### New Capabilities

- `commercial-audio-boundary-control`: Calibrated source admission, privacy-safe warm calibration transfer, bounded first-speech delivery, explicit terminal recovery, and stage-level acceptance evidence for commercial realtime interviews.

### Modified Capabilities

- `streamlined-interview-entry`: Audio-assisted entry requires fresh verified source and provider readiness, and transfers that ready state atomically into live capture without a cold local detector.

## Impact

- Desktop companion VAD/endpointing, preparation monitor, warm handoff, diagnostics, version metadata, packaging, and regression fixtures.
- Backend realtime ASR finalization/watchdog settings, safe runtime evidence, event lifecycle, pinned active-connection selection, binding conflict protection, and tests.
- Web preparation entry, automatic background readiness, and transcript terminal presentation/reconciliation tests.
- Production Backend and Web deployment, signed macOS arm64 companion 1.2.7 installation, and documented rollback artifacts.
- Web sound-gate rollback and signed macOS arm64 companion 1.2.8 local acceptance build for prompt preparation-to-live promotion.
- No raw audio, transcript text, API keys, or personal data is added to diagnostics.
