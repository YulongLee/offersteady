# Realtime interview runtime

## Production path

```text
Swift microphone + ScreenCaptureKit system audio
  -> Electron IPC control boundary
  -> one authenticated WebSocket v2 per interview
  -> bounded FastAPI ingress queues per role
  -> persistent Qwen realtime ASR sessions per role
  -> Redis runtime snapshot and bounded event stream
  -> cursor-based SSE web consumer
```

The packaged desktop uses Swift as the production capture owner. Browser audio is a development compatibility path and must not run beside the native owner. Raw PCM stays in bounded memory and is never stored in Redis, PostgreSQL, OSS, diagnostics, or support reports.

## Protocol and recovery

- Protocol version: `2.0`.
- One publisher token and one WebSocket carry `microphone` and `system` logical channels.
- Each channel has an independent sequence. The gateway acknowledges the highest contiguous accepted sequence and explicitly reports gaps.
- The desktop keeps at most 64 frames, approximately two seconds of 16 kHz mono PCM, and drops the oldest interim frame first.
- A reconnect reuses the publisher token and resumes from backend receipts for that publisher.
- Web presence is diagnostic only. Refreshing the page does not revoke the desktop media lease.
- The web consumer stores the latest activity cursor in session storage and resumes SSE snapshots from that cursor.

## State ownership

- Redis: desktop registrations, bindings, publisher leases, latest frame receipts, transient transcript state, event cursor and bounded operational events.
- PostgreSQL: durable interview metadata and only user-approved transcript retention.
- Process memory: bounded audio queues and active provider socket handles.
- OSS: never used for realtime audio.

## Feature controls

- `OFFERSTEADY_REALTIME_TRANSPORT_MODE=websocket-v2`
- `OFFERSTEADY_REALTIME_LEGACY_HTTP_ENABLED=false`
- `OFFERSTEADY_REDIS_URL=redis://redis:6379/0`
- `OFFERSTEADY_REDIS_REALTIME_REQUIRED=true` in production.
- `OFFERSTEADY_REALTIME_TRANSCRIPT_PERSISTENCE_ENABLED=false` by default; enable only after explicit user consent.
- `OFFERSTEADY_REALTIME_TRANSCRIPT_RETENTION_DAYS=30` when approved persistence is enabled.

Redis runtime snapshots and event streams expire after two hours by default. Approved final transcripts may be copied to PostgreSQL with an expiry timestamp; interim text is never archived.

Rollback enables the legacy HTTP flag only for sessions pinned to the old protocol. A running session must not switch protocols midway.

## Privacy-safe diagnostics

Allowed diagnostics include trace IDs, session-safe IDs, channel, sequence, queue depth, durations, dropped-frame counts, reconnect counts and provider error codes. Logs and reports must not contain PCM payloads, access tokens or transcript text.

## Release gates

The commercial path is not release-ready until the repository tests and a consented local acceptance run confirm:

- Final transcript latency p95 at or below two seconds on the reference network.
- Control API latency p95 at or below 500 milliseconds.
- Recovery within five seconds after a five-second interruption.
- A 30-minute dual-channel soak with bounded sockets, file descriptors, memory, queues and ASR sessions.
- Device switching, permission denial, backend restart and web refresh recovery.
