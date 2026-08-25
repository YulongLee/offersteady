## Production Path Audit

### Backend

1. `DashScopeRealtimeAsrGateway._receiver_loop` receives provider revisions and calls the registered partial listener.
2. `RealtimeSpeechService._publish_provider_partial` creates a monotonic transcript revision, saves it, then emits `transcript-updated`; Stable Partial observation runs afterward.
3. `RedisRealtimeSpeechRepository.save_event` performs one Redis XADD per event; `wait_for_events_after` performs blocking XREAD without a consumer group and adds the XREAD timestamp.
4. `stream_session_runtime` converts normal updates to event deltas, calls `observe_sse_delivery`, and yields one SSE frame. Response headers are `text/event-stream`, `Cache-Control: no-cache`, and `X-Accel-Buffering: no`.
5. `infra/nginx/default.conf` sets `proxy_buffering off`.

### Browser and React

1. `BackendInterviewAppAdapter.subscribeRealtimeSession` reads response chunks, parses SSE frames, materializes transcript deltas, and schedules product state delivery on one `requestAnimationFrame`.
2. Multiple events received before that frame are retained for delivery ACK but `pendingSnapshot` is replaced by the latest materialized state, so intermediate revisions may intentionally not enter product React state.
3. `ConversationMonitor` renders projected transcript turns and reports a parent-level render ACK.
4. `ProgressiveTranscriptText` maintains a second `visibleText` state and advances it every 32ms. The current effect depends on `text`, so a new revision clears and recreates the interval; the existing parent-level ACK does not prove the new text was visibly committed or painted.

### Existing Timing / Coalescing Points

- Backend XREAD blocks for `realtime_event_block_ms`, but a new XADD wakes the active read.
- SSE keepalive polling does not batch product events after XREAD returns.
- Browser uses one `requestAnimationFrame` to coalesce product state updates.
- Visible transcript uses a 32ms `setInterval` progressive reveal.
- No Stable Partial, Question Predictor, RAG or answer path gates `_save_event` for provider partials.

### Diagnostic Gaps

- Redis XADD start/complete are not attached to the per-revision trace.
- Browser chunk receive and event parse are currently one timestamp.
- Store update start/complete are not separated.
- React parent render is treated as visible render even though `ProgressiveTranscriptText` may still show an older string.
- There is no revision count reconciliation or gap report by stage.
- There is no tester-visible overlay.

## Implemented Diagnostic Evidence

- Provider Partial revisions retain one `traceId`, `eventId`, `utteranceId`, `segmentId`, revision, channel and text length; transcript text is not written to the performance trace.
- Redis records XADD start/complete and XREAD receive separately. The SSE event merges the authoritative bounded trace before yield, so the Browser receives the same revision identity even though Redis cannot know XADD completion before the XADD call returns.
- The SSE generator records yield and explicitly reports the underlying HTTP chunk-write timestamp as unavailable.
- Browser diagnostics distinguish raw stream chunk receipt, SSE parse, product store update start/complete, React render/commit and next-frame paint.
- Browser/React detailed diagnostics and the fixed overlay are enabled only by `subtitleDiagnostics=1`; normal pages do not poll the diagnostic summary or render the overlay.
- The existing one-frame Browser coalescing and 32ms progressive-visible-text timer remain unchanged for evidence collection.

## Enable / Disable

- Enable only for the visible test page by appending `?subtitleDiagnostics=1` to the interview URL. If the URL already has a query string, append `&subtitleDiagnostics=1` instead.
- Keep the page in the foreground; the overlay reports `visibility: visible`. Hidden samples remain counted but are excluded from visible-stage reporting.
- Disable by removing `subtitleDiagnostics=1` and reloading. The overlay, 2-second diagnostic summary poll, Browser revision store and commit/paint acknowledgements then stop.
- No Companion restart is required for enabling or disabling this Browser diagnostic view.

## Deterministic Verification

- Backend: `304 passed, 14 skipped` across `apps/backend/tests`.
- Web: `286 passed` across 42 test files.
- Web type check passed.
- Production Web build passed with the production environment guard enabled.
- `openspec validate diagnose-live-subtitle-revision-delivery --strict` passed.
