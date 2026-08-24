## Context

OfferSteady currently has several overlapping realtime implementations across the Swift capture helper, Electron main process, Electron renderer, FastAPI HTTP frame ingestion, in-process ASR queues, and web heartbeat/SSE consumers. Production diagnostics have shown duplicate publishers, thousands of open HTTPS connections, silent 100 ms chunks treated as final utterances, ASR queues delayed by more than 50 seconds, backend file-descriptor exhaustion, and web sessions that require manual refresh after a backend restart.

The product still needs the same two-channel experience: the candidate microphone is labelled `candidate`, system output is labelled `interviewer`, and the live web workspace receives ordered transcript updates. Raw audio is sensitive and remains ephemeral.

Target topology:

```text
macOS native capture supervisor
  microphone ----\
                  +--> bounded local buffer --> authenticated WebSocket
  system audio --/                                  |
                                                       v
                                            realtime gateway
                                                       |
                                  +--------------------+--------------------+
                                  |                                         |
                           candidate ASR WS                         interviewer ASR WS
                                  |                                         |
                                  +--------------------+--------------------+
                                                       v
                                  stable partial + context prefetch
                                                       |
                                            Redis event stream
                                                       |
                                      cursor-based web subscription
```

## Goals / Non-Goals

**Goals:**

- Establish exactly one capture owner and one transport supervisor per desktop session.
- Keep persistent, role-scoped ASR sessions instead of creating recognition work per short frame.
- Bound every queue and connection count, with deterministic overload behavior.
- Recover desktop transport, ASR adapters, and web consumers independently after transient failures.
- Preserve session and cursor state across backend worker or container restart.
- Make every stage observable without logging raw audio or transcript text by default.
- Deliver a macOS Apple Silicon MVP that can pass soak, reconnect, and latency acceptance gates.
- Keep per-frame media processing on session-local memory and direct Redis keys rather than PostgreSQL or a global serialized snapshot.
- Preserve explicit answer activation: realtime speech may prepare context but never starts an LLM answer before a user click.

**Non-Goals:**

- Windows support, mixed-channel diarization, raw audio recording, multi-device mixing, or offline transcription.
- Reworking answer generation, screenshot answers, RAG, materials, authentication, billing, or the established web visual design.
- Guaranteeing capture from hardware or applications that macOS does not expose through supported public APIs.

## Decisions

### 1. Swift is the only production audio capture owner

The packaged Swift runtime will own microphone and system-output capture. Electron will expose controls and status through IPC but will not create a second WebAudio or main-process capture pipeline while native capture is active.

For supported macOS versions, ScreenCaptureKit will provide system audio and, where available, microphone stream outputs. An AVAudioEngine microphone adapter can remain behind the same native supervisor for compatibility, but both paths must emit the same normalized frame contract.

Alternative considered: keep Electron WebAudio as an automatic fallback. Rejected for the commercial path because silent/dead tracks, permission identities, and duplicate ownership are difficult to distinguish. A fallback may be reintroduced only as an explicit degraded mode with mutual exclusion and acceptance tests.

### 2. Use one authenticated desktop WebSocket with two logical channels

The desktop will open one WebSocket per active interview and multiplex `microphone`, `system`, health, resume, and control messages. Audio envelopes contain protocol version, session lease, channel, sequence, capture timestamp, codec, sample rate, and payload.

The default payload is 16 kHz mono PCM for initial compatibility. Opus can be negotiated later without changing lifecycle semantics.

Alternative considered: continue HTTP POST ingestion with larger chunks. Rejected because it retains connection churn, weak cancellation, and ambiguous per-request ordering. HTTP remains only as a temporary compatibility path during migration.

### 3. Separate control plane, media plane, and event plane

- REST control plane: pair device, start/stop interview, issue short-lived transport tokens, and query snapshots.
- WebSocket media plane: desktop audio and transport acknowledgements.
- Redis event plane: ordered transcript, health, and lifecycle events consumed by the web application.

Web presence is advisory. Loss of a web heartbeat changes presence state but does not immediately invalidate a valid desktop lease. Capture stops only on explicit session stop, lease expiry, logout/revocation, or privacy control from the desktop.

Alternative considered: use web heartbeat as the media authorization gate. Rejected because a browser refresh or SSE reconnect can interrupt capture even when the interview remains active.

### 4. Maintain one persistent ASR connection per role

The realtime gateway creates at most one ASR adapter session for each active `candidate` and `interviewer` channel. Audio is appended to that provider session in order. The client endpoint controller is authoritative for the commercial path because measured provider VAD finalization has a materially longer tail. Provider VAD and semantic completeness remain advisory signals; a bounded hard timeout always closes an abandoned turn. Manual commit is allowed only for a complete client-detected utterance.

Provider-specific event formats stay inside a replaceable ASR adapter. Domain transcript events do not expose Qwen-specific fields.

Alternative considered: submit each chunk as a standalone ASR request. Rejected because service time exceeded arrival rate and produced unbounded queues and phantom short transcripts.

The control plane prewarms both enabled role connections as soon as a session enters `live`. Prewarming carries no audio and does not create a transcript segment. The first real frame therefore appends to an already configured provider session. Prewarm is idempotent and may fall back to the existing first-frame lazy creation if the provider is temporarily unavailable.

Realtime ASR usage is metered once per active session minute, not once per channel. A stable usage identifier composed from session id and wall-clock minute index makes settlement idempotent across duplicate timers, browser refreshes, desktop reconnects, and backend workers. An active time pass has priority and records zero-point pass usage; otherwise each minute costs five points. Paused capture does not open a new billable minute. Insufficient balance pauses capture and closes provider sessions instead of allowing unbounded unpaid usage.

### 5. Use Redis for ephemeral runtime and PostgreSQL for durable product data

Redis stores session leases, device presence, transport resume offsets, active publisher metadata, bounded transcript event streams, consumer cursors, and short-lived idempotency keys. PostgreSQL stores durable session metadata and approved final transcript records. Raw audio is not written to either store.

Alternative considered: keep all runtime state in one FastAPI worker. Rejected because restarts lose publisher/consumer state and multiple workers cannot share authoritative runtime ownership.

### 6. Make reconnect cursor-based and idempotent

Desktop messages use monotonically increasing per-channel sequences. The gateway acknowledges the highest contiguous sequence. After reconnect, the desktop resumes only within its bounded in-memory buffer and never replays already acknowledged audio.

Web transcript events have monotonic stream cursors and stable transcript revision identifiers. The web reconnects with its last cursor, applies newer revisions idempotently, and falls back to an authoritative snapshot if the cursor has expired.

### 7. Enforce hard resource limits and explicit degradation

- Desktop audio buffer: at most two seconds per channel.
- Gateway ingress buffer: at most two seconds per channel.
- One desktop transport and at most two ASR provider sessions per active interview.
- Old interim audio/events are dropped before final utterances when overloaded.
- No retry loop may create a new attempt while the previous attempt remains in flight.
- Backoff includes jitter and an upper bound; terminal authorization failures do not retry indefinitely.

The UI shows `capturing`, `streaming`, `reconnecting`, `degraded`, or `stopped` from the authoritative runtime state.

### 8. Stabilize application identity and permissions

The commercial app uses one fixed bundle identifier, Developer ID signature, notarization, and Keychain-backed device credentials. A release upgrade does not regenerate the device ID or require machine-code rebinding. Local development uses a fixed development identity and never runs privacy reset as part of ordinary app startup.

### 9. Establish measurable release gates

Under the supported reference environment, speech-to-web transcript latency must be p95 at or below two seconds, control requests p95 at or below 500 ms, and transport reconnect at or below five seconds. A 30-minute two-channel soak must show bounded file descriptors, connections, memory, queues, and duplicate transcript rate.

### 10. Keep the media and transcript hot path session-local

WebSocket authentication, user ownership and interview lifecycle are validated when a transport is established and periodically on a coarse control-plane lease. An accepted audio frame must not open a PostgreSQL connection. Per-channel sequence, receipt and publisher activity are updated with bounded session-scoped memory and direct Redis hash fields. Publisher lifecycle state is written only when it changes, never twice per audio revision.

Redis recovery data is split by session, publisher and device. The commercial path must not acquire one global lock and serialize every device, binding, heartbeat and publisher for each frame.

### 11. Deliver minimal monotonic deltas

Transcript, candidate-question and answer-token events carry a global cursor plus stable segment/task identity and revision. A normal SSE update contains only new events. Full transcripts, candidates, runtime and answer state are read only for initial entry, expired-cursor recovery or an explicit diagnostic snapshot.

The browser applies higher cursors and higher segment revisions monotonically. A final transcript cannot be replaced by a late partial. Performance acknowledgements are metrics and do not re-enter the product event stream.

### 12. Stabilize interviewer partials and prefetch context without automatic answers

Only the interviewer channel feeds a stable-partial detector. Stable prefixes may update a predicted retrieval query and prepare resume, JD and knowledge context in a short-lived session cache. Candidate-channel speech remains available for captions and review but cannot become the active interviewer question.

Turn completion produces an authoritative candidate question. The system still waits for explicit user activation. When the user selects quick answer, the backend freezes `questionId`, `questionRevision`, `questionText`, `clickedAtMs` and the compatible prefetch revision. Later ASR revisions cannot mutate the answer already in progress.

### 13. Send audio immediately and retain only a rolling recovery window

Each channel sends negotiated 20-100 ms frames as soon as they are available. Its two-second ring buffer is a rolling copy for acknowledgement recovery and pre-speech context; it is never a batching delay. Binary WebSocket audio frames are preferred after protocol negotiation, while protocol-v2 JSON/base64 remains a bounded compatibility mode for already published clients.

## Risks / Trade-offs

- [Screen/system audio permissions remain controlled by macOS] -> Use supported public APIs, stable signing identity, explicit readiness checks, and actionable permission UI.
- [Bluetooth devices can change sample format or disappear] -> Observe device changes in the native supervisor, reconfigure safely, and preserve the session while reporting a degraded channel.
- [Redis adds operational complexity] -> Use one managed or Compose Redis instance for MVP, persistence only where needed, health checks, and documented backup/eviction policy.
- [WebSocket infrastructure is more complex than HTTP] -> Keep the protocol small, versioned, load-tested, and isolated in a dedicated gateway module.
- [Provider VAD may split interview speech imperfectly] -> Retain configurable client noise gating, provider VAD settings, transcript revision handling, and synthetic eval fixtures.
- [Two prewarmed provider sessions increase idle ASR cost] -> Open them only for a live, capturing interview, meter one session minute rather than two channels, close them on pause/end, and expose per-session usage metrics.
- [Migration can temporarily support two protocols] -> Feature-flag legacy ingestion, prevent mixed ownership per session, and remove legacy code immediately after acceptance.

## Migration Plan

1. Freeze overlapping legacy realtime changes and designate this change as the source of truth.
2. Define versioned transport and transcript contracts plus synthetic fixtures.
3. Introduce Redis runtime state and the realtime gateway behind a disabled feature flag.
4. Implement microphone-only native capture through the new transport and persistent candidate ASR session.
5. Add cursor-based web consumption and restart/reconnect recovery.
6. Add system-output capture and the interviewer ASR session.
7. Run shadow diagnostics without exposing duplicate transcripts to users.
8. Enable the new path for internal accounts, then a small percentage of test users.
9. Pass latency, soak, privacy, restart, hot-plug, and permission acceptance gates.
10. Disable and remove HTTP-per-frame publishing, duplicate main/renderer capture, and legacy heartbeat authorization.

Rollback keeps the legacy path feature-flagged during the migration window. A session is assigned one protocol at creation and never switches transport mid-session. Redis and protocol additions are backward-compatible until legacy removal.

## Open Questions

- Minimum supported macOS version for direct ScreenCaptureKit microphone output versus the compatibility AVAudioEngine adapter.
- Whether MVP Redis should be managed or colocated in the current single-server Compose deployment.
- Initial codec choice after PCM validation: retain PCM for simplicity or negotiate Opus before external beta.
- Retention policy for user-approved final transcripts and whether transcript persistence is opt-in per interview.
- Exact reference hardware and network profile used for commercial SLO certification.
