## Why

The current realtime interview assistant couples native capture, Electron polling, web heartbeats, HTTP frame ingestion, in-memory queues, and ASR lifecycle management. This has produced duplicate publishers, connection leaks, unbounded ASR backlog, phantom transcripts, and sessions that stop after a web refresh or backend restart, so the realtime experience is not reliable enough for MVP release or commercial use.

## What Changes

- Replace overlapping main-process, renderer, and fallback capture ownership with one supervised native macOS capture runtime for microphone and system-output channels.
- Replace per-frame HTTP ingestion with bounded, long-lived realtime transport and explicit backpressure, reconnect, and session-resume behavior.
- Maintain one persistent Qwen ASR Realtime session per active audio role, using streaming append events and VAD/utterance commits instead of treating short PCM frames as independent recognition jobs.
- Prewarm the enabled microphone and system-audio provider sessions when the interview becomes live, and meter active realtime interview minutes through the existing idempotent membership/points ledger at 5 points per minute.
- Separate desktop capture lifecycle from web-page presence so a transient page heartbeat failure does not silently destroy the audio session.
- Persist recoverable realtime session, device binding, publisher, consumer cursor, and lease state outside a backend worker process.
- Make the web live page reconnect automatically, resume from its last event cursor, and render an authoritative runtime state instead of inferring health from polling side effects.
- Add bounded queues, overload shedding, end-to-end trace identifiers, stage timings, health checks, and commercial acceptance SLOs.
- Remove PostgreSQL lookups, global Redis snapshot rewrites, and whole-workspace refreshes from the per-frame transcript hot path.
- Stabilize interviewer partial revisions, prefetch resume/JD/knowledge context in parallel, and freeze the authoritative question revision only when the user explicitly selects quick answer.
- Deliver transcript and answer deltas through one ordered event stream while keeping snapshots exclusively for initial load and bounded recovery.
- Stabilize desktop device identity and permission behavior across relaunches and production upgrades.
- **BREAKING**: retire legacy HTTP-per-audio-frame publishing and duplicate renderer/main-process capture ownership after migration validation.
- Keep raw interview audio ephemeral by default; persist only user-approved transcripts and operational metadata required for recovery and diagnostics.

### MVP Scope

- macOS Apple Silicon desktop companion.
- One candidate microphone channel and one interviewer/system-output channel.
- One active interview per desktop device.
- Qwen ASR Realtime behind a replaceable server-side adapter.
- Web live transcript delivery with automatic reconnect and bounded replay.
- Synthetic and consented local acceptance fixtures only; no raw production audio retention.

### Non-Goals

- Windows capture support in this change.
- Multi-device audio mixing for one interview.
- Long-term raw audio recording, meeting recording, or post-interview audio playback.
- Automatic speaker diarization inside a mixed channel; roles remain channel-derived.
- Changing screenshot-answer semantics, manual-question semantics, authentication, or the explicit user action required to generate an answer.

## Capabilities

### New Capabilities

- `native-dual-channel-capture`: Own microphone and system-output capture in one supervised native runtime with stable device selection, permissions, health, and bounded local buffering.
- `realtime-audio-transport`: Stream ordered audio over authenticated long-lived connections with backpressure, reconnect, resume, and legacy transport migration behavior.
- `persistent-realtime-asr-session`: Maintain role-scoped Qwen ASR Realtime sessions with correct append, VAD or commit, transcript normalization, and provider recovery semantics.
- `resilient-interview-runtime`: Persist realtime leases, bindings, runtime state, and event cursors so desktop, web, and backend processes can recover independently.
- `live-transcript-delivery`: Deliver ordered, role-labelled transcript events to the live web workspace with cursor replay, deduplication, and visible degraded states.
- `realtime-pipeline-observability`: Enforce queue limits, connection limits, stage metrics, trace correlation, privacy-safe diagnostics, health checks, and release SLO gates.
- `stable-question-prefetch`: Stabilize interviewer partials, predict retrieval queries, prepare bounded context, and freeze a question revision only on explicit quick-answer activation.
- `realtime-hot-path`: Keep media ingestion and incremental delivery independent from PostgreSQL and global runtime snapshots.

### Modified Capabilities

None. Existing main specs do not yet define the realtime desktop-to-web contract; legacy realtime changes will be superseded rather than silently altering unrelated capabilities.

## Impact

- Desktop: Swift capture runtime, Electron IPC boundary, device identity storage, permissions, release signing, and removal of duplicate capture/poll loops.
- Backend: realtime gateway, ASR adapter lifecycle, bounded queues, session ownership, Redis-backed leases/events, transcript persistence, and health/readiness behavior.
- Web: live-session subscription, heartbeat semantics, cursor storage, reconnect behavior, and runtime status presentation.
- Answer fast path: question-revision snapshots and prepared-context reuse without enabling automatic answers.
- Billing: one session-scoped realtime-minute usage unit per active minute, with time-pass priority, five-point fallback charging, and idempotent settlement across refreshes and reconnects.
- Infrastructure: Redis becomes required for commercial realtime deployment; reverse proxy must support WebSocket upgrades and long-lived connections.
- Protocol: versioned desktop handshake, audio envelope, control events, transcript events, resume cursors, and explicit compatibility window for legacy clients.
- Privacy: raw PCM/Opus remains memory-only with short bounded buffers; logs and diagnostics retain counts, timings, identifiers, and error codes but not audio payloads or transcript text by default.
