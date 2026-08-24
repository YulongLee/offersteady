## Why

Production interviews frequently leave visible utterances in “转写中” because finalization depends on a noise-sensitive desktop energy boundary; repeated partial revisions keep the UI active indefinitely and adjacent-turn projection can make already confirmed text appear non-final again. The realtime path streams audio and interim text, but its end-of-turn, terminal-state, overload, and recovery guarantees are not yet reliable enough for a commercial interview experience.

## What Changes

- Introduce a hybrid end-of-turn controller that combines source-specific local speech evidence with provider completion signals, adaptive noise handling, bounded hard deadlines, and deterministic forced-final recovery.
- Preserve stable transcript identities and monotonic lifecycle states so a confirmed turn can never return to “转写中”, including after adjacent-turn projection, duplicate delivery, reconnect, or stale partial recovery.
- Make final audio frames lossless relative to interim frames: overload may coalesce or discard obsolete partials, but must reserve capacity for and explicitly acknowledge terminal frames.
- Add an ASR watchdog that closes or recovers stalled turns, preserves the last stable text without billing or answering it automatically, and rebuilds only the affected source connection.
- Keep quick answer and screenshot answer explicitly user-triggered; speech recognition alone must not create an answer task or consume answer points.
- Add privacy-safe end-to-end timings, finalization-reason metrics, queue-pressure metrics, and commercial SLO release gates using synthetic audio fixtures.
- Roll out compatibility-first: backend and Web changes support existing companions, while the improved local end-of-turn controller ships in a new signed desktop version with feature-flagged rollback.
- Prefer an isolated Beta stack when capacity permits. When the operator explicitly declines a parallel Beta because the current single server lacks safe headroom, require complete local verification and a compatibility-first production canary with new recovery enforcement disabled by default, recorded rollback artifacts, and immediate health checks before publishing a new companion manifest.

### MVP Scope

- Microphone and system-output channels used by the current Electron companion on supported macOS and Windows releases.
- Existing Qwen Realtime ASR provider behind the current replaceable backend adapter.
- Existing Web session SSE and explicit quick-answer/screenshot-answer controls.
- No raw audio persistence; tests use generated, synthetic, or explicitly authorized fixtures.

### Non-Goals

- Replacing the ASR model, answer model, prompts, billing rates, or knowledge retrieval.
- Automatically generating answers from recognized speech.
- Recording meetings, persisting raw PCM, or adding speaker diarization to mixed audio.
- Redesigning the live interview page or changing screenshot-answer behavior.

## Capabilities

### New Capabilities

- `commercial-live-transcript-finalization`: Defines hybrid turn boundaries, monotonic transcript state, terminal-frame delivery, stalled-turn recovery, privacy-safe observability, compatibility, and release SLOs for commercial realtime interviews.
- `isolated-realtime-beta-release`: Defines the isolated Beta environment, test URL and companion, production separation, promotion approval, and rollback contract.

### Modified Capabilities

None. The main spec store does not currently contain the desktop-to-Web realtime transcript contract; this change supersedes overlapping historical change behavior without modifying unrelated main capabilities.

## Impact

- Desktop: audio segmenter, realtime publisher backpressure/acknowledgement, source-health telemetry, runtime feature flags, tests, versioned production packages.
- Backend: realtime ingest queue, ASR session/turn controller, final reconciliation, source-scoped recovery, metrics, and synthetic load/regression tests.
- Web: transcript reducer/projection, terminal-state presentation, reconnect reconciliation, and focused UI tests.
- Protocol: backward-compatible optional fields/events for terminal acknowledgement, finalization reason, and source recovery; no removal of current fields or endpoints during the compatibility window.
- Infrastructure: no new service or database is required; existing Redis session events remain the delivery mechanism.
- Preview infrastructure: an isolated Beta Compose option remains available, but it is not started on a resource-constrained production host unless the operator explicitly selects that path.
- Privacy: audio remains in bounded volatile memory, transcript persistence behavior is unchanged, and telemetry contains timings/counters/error codes rather than audio or transcript content.
