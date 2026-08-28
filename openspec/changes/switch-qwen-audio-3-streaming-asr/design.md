## Context

OfferSteady currently maps source-scoped desktop PCM segments onto the Qwen3 Realtime protocol at `/api-ws/v1/realtime`. The authorized `qwen-audio-3.0-asr-flash-streaming` model uses the DashScope inference-task protocol at `/api-ws/v1/inference`: a connection accepts `run-task`, raw binary audio, `result-generated`, and `finish-task` events. A live synthetic Chinese sample succeeded through the public endpoint, while the Workspace-specific endpoint still returned HTTP 403 `Endpoint.AccessDenied`.

The application already owns segmentation, bounded queues, partial publication, finalization, billing, source isolation, and transcript reconciliation. The provider adapter must preserve those contracts rather than move them into the desktop or Web client.

## Goals / Non-Goals

**Goals:**

- Select the provider protocol explicitly and make Qwen Audio 3 streaming the test target.
- Keep one reusable WebSocket per session/source and one provider task per application segment.
- Publish provider intermediate results immediately and map the terminal sentence result to the application final.
- Keep the prior Qwen3 gateway selectable for rollback without code reversion.
- Preserve privacy-safe diagnostics, bounded waits, and source-local failure recovery.

**Non-Goals:**

- No automatic model fallback inside a live segment; that could duplicate billed audio or merge transcripts from two providers.
- No AOQ client migration, model quality claim, desktop capture change, layout change, prompt change, or transcript persistence change.
- No Workspace endpoint use until Alibaba Cloud grants that endpoint independently.

## Decisions

### Add a separate inference-task gateway

Implement a new adapter instead of branching deeply inside the existing Qwen3 gateway. The protocols have different connection bootstrap, audio framing, completion events, and reuse semantics. Separate adapters keep the external provider replaceable and make rollback a dependency-wiring decision.

Alternative considered: change only the model and URL in the existing gateway. Rejected because `session.update`, base64 JSON audio append, and manual commit are invalid for the new model.

### Reuse connections but scope tasks to application segments

Each microphone/system source keeps an independent WebSocket. A task is started during warmup, receives raw binary PCM for one application segment, and is finished on the application terminal frame. After `task-finished`, the adapter starts the next task on the same connection so the next utterance remains warm.

Alternative considered: keep one provider task for an entire interview and rely only on server VAD. Rejected for the first switch because provider sentence boundaries can diverge from the application's terminal IDs and complicate authoritative final acknowledgements.

### Treat provider sentence final as authoritative and task-finished as lifecycle completion

`result-generated` with non-empty text and `sentence_end=false` becomes a partial revision. `sentence_end=true` becomes the authoritative segment text. `task-finished` confirms provider lifecycle completion. Empty heartbeat/sentence-begin events do not create visible transcript revisions.

### Use the public inference endpoint explicitly

The new adapter defaults to `wss://dashscope.aliyuncs.com/api-ws/v1/inference`, because it passed authorization and real transcription. It must not derive a Workspace domain for this protocol while that endpoint returns `Endpoint.AccessDenied`.

### Keep rollback configuration explicit

`OFFERSTEADY_REALTIME_ASR_PROTOCOL` selects `qwen-audio-task` or `qwen3-realtime`. Model and URL remain independent settings. Rollback restores the prior protocol/model/URL together and restarts Backend; an active provider task is never migrated in place.

## Risks / Trade-offs

- [Provider final may arrive before or after `finish-task`] → Wait for both authoritative final text and bounded task completion, while retaining the latest non-empty result.
- [Connection reuse after a failed task may be unsafe] → Close only the affected source socket and recreate it on retry.
- [New server VAD may change sentence timing] → Use low-latency VAD mode (`semantic_punctuation_enabled=false`, bounded `max_sentence_silence`) and preserve desktop terminalization.
- [A model switch can regress accuracy despite lower latency] → Expose model/protocol in content-free diagnostics and retain immediate configuration rollback.
- [Automatic fallback could duplicate transcripts and cost] → Do not auto-fallback mid-segment; surface a retryable provider error to the existing source recovery path.

## Migration Plan

1. Ship the new adapter and tests while the old protocol remains configured.
2. Run focused/full Backend tests and a live synthetic-audio check through the new adapter.
3. Set protocol, model, and public inference URL together in the test/production server configuration and restart only Backend.
4. Verify health, source prewarm, partial/final delivery, and provider diagnostics.
5. Roll back by restoring `qwen3-realtime`, `qwen3-asr-flash-realtime-2026-02-10`, and the public `/api-ws/v1/realtime` URL, then restarting Backend.

## Open Questions

- Workspace-specific `/api-ws/v1/inference` remains unavailable for the current key; public endpoint use is the confirmed deployment constraint.
- Commercial quality and latency comparison requires user acceptance on real interview audio after the protocol-correct switch.
