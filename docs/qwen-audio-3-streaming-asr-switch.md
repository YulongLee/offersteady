# Qwen Audio 3 streaming ASR switch

## Selected test configuration

```text
OFFERSTEADY_REALTIME_ASR_PROTOCOL=qwen-audio-task
OFFERSTEADY_REALTIME_ASR_MODEL=qwen-audio-3.0-asr-flash-streaming
OFFERSTEADY_REALTIME_ASR_INFERENCE_WS_URL=wss://dashscope.aliyuncs.com/api-ws/v1/inference
OFFERSTEADY_REALTIME_ASR_MAX_SENTENCE_SILENCE_MS=300
```

The API key remains in the server secret environment. The Workspace-specific inference endpoint is not selected because the current workspace returned HTTP 403 `Endpoint.AccessDenied`; the public endpoint completed both authorization and synthetic-speech transcription.

## Verified behavior

- The protocol adapter waits for `task-started` before sending raw 16 kHz mono PCM as binary WebSocket frames.
- One provider WebSocket is isolated per interview/source and is reused across application segments.
- Non-empty `result-generated` events publish monotonic partial revisions; empty heartbeat/sentence-begin events stay invisible.
- Production reuses one WebSocket per source but finishes and starts a provider task for each local utterance. Cross-utterance task reuse remains experimental and disabled because production verification observed a provider `CLIENT_ERROR request timeout` after approximately 23 seconds of task inactivity.
- A failed or ambiguous task closes only the affected source connection.
- `task-failed` keeps the first provider code/message and source/task/connection attribution even when the provider subsequently closes the socket.
- A reconnect replays only the bounded rolling PCM tail and stitches it to an in-memory transcript checkpoint; neither audio nor checkpoint text is persisted or logged.
- Audio, credentials, and transcript content are excluded from runtime diagnostics.
- The provider VAD sentence-end silence is set to 300 ms. This reduces Final latency after speech stops but does not alter the provider's Partial revision cadence.

The 2026-08-28 local live-adapter check returned five transcript revisions, correct final synthetic text, and no provider failure. First partial was observed at approximately 656 ms from the local test start. This is a connectivity/behavior sample, not a commercial p95 claim.

## Rollback tuple

Restore all three values together and restart Backend:

```text
OFFERSTEADY_REALTIME_ASR_PROTOCOL=qwen3-realtime
OFFERSTEADY_REALTIME_ASR_MODEL=qwen3-asr-flash-realtime-2026-02-10
OFFERSTEADY_REALTIME_ASR_WS_URL=wss://dashscope.aliyuncs.com/api-ws/v1/realtime
```

Do not change providers inside an active segment. Rollback applies to newly created provider connections after Backend restart.
