# Realtime interview runtime

## Production path

```text
Electron microphone + display loopback system audio
  -> Electron IPC control boundary
  -> one authenticated WebSocket v2 per interview
  -> bounded FastAPI ingress queues per role
  -> persistent Qwen realtime ASR sessions per role
  -> Redis runtime snapshot and bounded event stream
  -> one cursor-based session SSE for transcript, explicit answer and screenshot lifecycle state
  -> monotonic web reducer and task-specific answer SSE for first-token delivery
```

The current packaged desktop uses one Electron renderer as the production capture and transport owner. The bundled Swift runtime remains an inactive migration path and must not run beside the renderer owner. Raw PCM stays in bounded memory and is never stored in Redis, PostgreSQL, OSS, diagnostics, or support reports.

The renderer treats `ended`, `muted`, a suspended/closed AudioContext, a stalled audio callback, and a previously active system track that becomes persistently silent as source-health failures. It rebuilds only the system source with bounded backoff so microphone capture and the live interview remain active.

## Protocol and recovery

- Protocol version: `2.0`.
- One publisher token and one WebSocket carry `microphone` and `system` logical channels.
- Each channel has an independent sequence. The gateway acknowledges the highest contiguous accepted sequence and explicitly reports gaps.
- The desktop keeps at most 64 frames, approximately two seconds of 16 kHz mono PCM, and drops the oldest interim frame first.
- A reconnect reuses the publisher token and resumes from backend receipts for that publisher.
- Web presence is diagnostic only. Refreshing the page does not revoke the desktop media lease.
- The web consumer stores the latest activity cursor in session storage, hydrates once, and then consumes ordered incremental events. A cursor outside the retained Redis range forces a fresh snapshot.
- Transcript confirmation never creates an answer task. Only a user click on quick answer, manual answer, or screenshot answer may start answer generation.
- The dedicated answer SSE remains responsible for token-by-token first response. Its lifecycle is also published into the session stream so reconnects and cross-device views converge on the same terminal state.
- Screenshot request stages (`requested`, `claimed`, `uploaded`, `vision-running`, terminal) use the same session event stream. Events contain identifiers and safe metadata only; screenshots and audio are never embedded.

## State ownership

- Redis: desktop registrations, bindings, publisher leases, latest frame receipts, transient transcript state, event cursor and bounded operational events.
- PostgreSQL: durable interview metadata and only user-approved transcript retention.
- Process memory: bounded audio queues and active provider socket handles.
- OSS: never used for realtime audio.

## Pause and resume privacy control

- The live web workspace sends `pause` or `resume` to the session capture control API; changing React state alone is not authoritative.
- The backend persists the latest capture control as a session event and exposes it in runtime and desktop pairing snapshots.
- While capture is `paused`, audio frames are discarded before receipt creation, ASR, transcript publication, billing usage, and activity updates.
- The desktop stops both its active realtime publisher and idle audio monitor while paused. Polling, page refresh, WebSocket reconnect, and desktop relaunch must not resume capture.
- Capture resumes only after an explicit `resume` command for the same live session. Ending a session remains terminal.

## Feature controls

- `OFFERSTEADY_REALTIME_TRANSPORT_MODE=websocket-v2`
- `OFFERSTEADY_REALTIME_LEGACY_HTTP_ENABLED=false`
- `OFFERSTEADY_REDIS_URL=redis://redis:6379/0`
- `OFFERSTEADY_REDIS_REALTIME_REQUIRED=true` in production.
- `OFFERSTEADY_REALTIME_TRANSCRIPT_PERSISTENCE_ENABLED=false` by default; enable only after explicit user consent.
- `OFFERSTEADY_REALTIME_TRANSCRIPT_RETENTION_DAYS=30` when approved persistence is enabled.

Redis runtime snapshots and event streams expire after two hours by default. Approved final transcripts may be copied to PostgreSQL with an expiry timestamp; interim text is never archived.

Rollback enables the legacy HTTP flag only for sessions pinned to the old protocol. A running session must not switch protocols midway.

For screenshot delivery, current desktop packages subscribe to the authenticated device event stream. The legacy `capture-requests/next` endpoint remains a compatibility and recovery path: the desktop performs a single non-overlapping check only after the push stream fails, then reconnects with bounded backoff. Older packages therefore remain usable during a staged rollout.

## Privacy-safe diagnostics

Allowed diagnostics include trace IDs, session-safe IDs, channel, sequence, queue depth, durations, dropped-frame counts, reconnect counts and provider error codes. Logs and reports must not contain PCM payloads, access tokens or transcript text.

Recommended event-flow metrics are session-stream reconnect count, resume success rate, event cursor lag, screenshot request-to-claim latency, screenshot terminal latency, fallback poll count, and duplicate event suppression count. A rise in fallback polls or cursor resets indicates push-path degradation even when the user-visible workflow still succeeds.

## Release gates

The commercial path is not release-ready until the repository tests and a consented local acceptance run confirm:

- Final transcript latency p95 at or below two seconds on the reference network.
- Control API latency p95 at or below 500 milliseconds.
- Recovery within five seconds after a five-second interruption.
- A 30-minute dual-channel soak with bounded sockets, file descriptors, memory, queues and ASR sessions.
- Device switching, permission denial, backend restart and web refresh recovery.
