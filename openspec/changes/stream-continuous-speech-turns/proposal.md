## Why

Continuous candidate and interviewer speech is currently finalized after very short pauses, so one spoken turn appears as many confirmed transcript cards instead of one progressively revised sentence. This damages readability, fragments question context, and makes automatic answers less reliable in real video interviews.

## What Changes

- Keep a stable transcript segment identity through normal breathing and thinking pauses while continuing to publish interim audio revisions.
- Use source-specific end-of-turn timing and a bounded maximum turn duration so candidate speech feels continuous without delaying interviewer question detection indefinitely.
- Make backend interim ASR delivery resilient to provider response timing instead of treating a short polling window as the boundary of visible streaming.
- Present adjacent revisions and safe same-speaker fragments as one progressive conversation turn, while preserving final boundaries and source roles.
- Build automatic interviewer questions from the completed interviewer turn rather than an isolated ASR fragment.
- Add privacy-safe synthetic regressions for continuous speech, short pauses, finalization, role changes, retries, and question triggering.

## Capabilities

### New Capabilities

- `continuous-live-transcription`: Continuous microphone and system-audio turns stream as stable revisions, finalize at meaningful boundaries, and provide complete turns to the live conversation and question-answer pipeline.

### Modified Capabilities


## Impact

- Desktop audio segmentation and packaged companion releases for macOS arm64, macOS x64, and Windows.
- Backend realtime ASR session handling, transcript event publication, question candidate construction, and associated telemetry.
- Web live conversation rendering and transcript reconciliation.
- Existing realtime protocol fields remain compatible; no raw audio, transcript, or personal-data retention policy changes are introduced.
