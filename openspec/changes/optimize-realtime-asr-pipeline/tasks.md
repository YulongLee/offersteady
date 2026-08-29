## 1. Baseline and Performance Instrumentation

- [x] 1.1 Add stage-level timing probes for capture, queue wait, ASR TTFT, final transcript latency, backend push, and frontend render latency.
- [x] 1.2 Add runtime counters for queue depth, dropped partial updates, connection recreations, CPU-sensitive allocation hotspots, and empty/phantom transcript suppression.
- [x] 1.3 Build a reproducible local performance benchmark flow and record the current baseline before refactoring.

## 2. Desktop Audio Pipeline Refactor

- [x] 2.1 Replace cumulative utterance payload generation with incremental PCM chunk streaming per source.
- [x] 2.2 Introduce source-scoped bounded buffering (RingBuffer or equivalent) and freshness-first backpressure rules for microphone and system audio.
- [ ] 2.3 Migrate capture callbacks toward AudioWorklet/native-producer-friendly boundaries and keep ScriptProcessor only as a fallback path.
- [ ] 2.4 Recalibrate silence gating and empty-audio suppression separately for source health, utterance start, and transcript publish eligibility.
- [x] 2.5 Reduce partial transcript chunk cadence to 150 ms and extend default persistent ASR idle reuse to 300 seconds.
- [x] 2.6 Tighten active-speech incremental PCM cadence to approximately 100 ms without resending prior audio bytes.

## 3. Backend Realtime ASR Pipeline Refactor

- [x] 3.1 Decouple ingest from transcription so audio receive paths return quickly after enqueueing work.
- [x] 3.2 Introduce persistent ASR sessions per `sessionId + sourceKind` with long-lived streaming workers.
- [x] 3.3 Implement source-local producer-consumer workers that send incremental audio, reconcile partial/final transcript events, and avoid synchronous request blocking.
- [x] 3.4 Add worker lifecycle, idle timeout, error recovery, and rollback-safe feature flags for the new pipeline.
- [x] 3.5 Coalesce adjacent incremental PCM frames under backlog while preserving all audio bytes and final delivery.
- [x] 3.6 Atomically supersede stale device bindings and publisher tokens when the same desktop moves to a new interview.
- [x] 3.7 Decouple provider WebSocket receive from PCM append with one persistent event receiver per session source.
- [x] 3.8 Track provider event and delivered revisions independently so between-frame partials are not skipped or duplicated.
- [x] 3.9 Remove session-wide transcript scans and stable-question work from the Provider Partial publication hot path.
- [x] 3.10 Make PCM coalescing backlog-adaptive so healthy 100ms frames enter the ASR sender immediately.
- [x] 3.11 Suppress provider-completed empty utterances without degrading publishers or recreating healthy ASR connections.
- [x] 3.12 Preserve first-cause Qwen task failures with source/task/connection attribution and isolate recoverable failure to one source.
- [x] 3.13 Replace all-or-nothing utterance replay with a bounded rolling PCM tail and in-memory overlap stitching.
- [x] 3.14 Reuse one healthy Qwen task across local utterances behind a rollback-safe feature flag with task-rollover fallback.
- [x] 3.15 Default production to per-utterance Qwen tasks on a persistent source WebSocket after the provider rejected idle continuous tasks.
- [x] 3.16 Keep prewarmed source WebSockets idle without an active Qwen task and lazily start each provider task on the next utterance's first audio frame.

## 4. Web Transcript Streaming and Overlay Efficiency

- [x] 4.1 Refactor live conversation state to reconcile partial and final transcripts by stable utterance identity instead of appending duplicate rows.
- [x] 4.2 Minimize UI update cost with incremental state updates, batching, and suppression of empty/phantom transcript renders.
- [x] 4.3 Preserve the current live workspace layout while updating diagnostics to reflect source-specific realtime latency and degradation states.
- [x] 4.4 Assemble the latest interviewer turn for quick answer, including a newer partial revision without mixing candidate speech into the question.
- [x] 4.5 Add bounded SSE reconnect backoff, stop healthy-stream polling, and prevent invalid-session retry storms.
- [x] 4.6 Make desktop registration startup-only in the renderer and heartbeat-only in the main process.
- [x] 4.7 Reset transient live state for newly created sessions and enforce session-scoped transcript reconciliation.
- [x] 4.8 Circuit-break invalid-session SSE recovery so polling, focus events, and reconnect timers cannot form a retry storm.
- [x] 4.9 Exit invalid live routes immediately and move synchronous Redis SSE reads off the FastAPI event loop.
- [x] 4.10 Reuse runtime diagnostics for two seconds during high-frequency SSE partial updates.
- [x] 4.11 Preserve ordered healthy transcript revisions through Redis/SSE and the Browser state adapter before presentation-only smoothing.
- [x] 4.12 Move runtime diagnostic aggregation off the transcript SSE hot path and deliver it as a separate single-flight update.
- [x] 4.13 Add bounded adaptive smoothing for received Partial text with immediate first character, shared frame scheduling, forced catch-up, and instant Final/reduced-motion fallback.
- [x] 4.14 Make realtime SSE snapshot-first and add keepalive-aware, cursor-resumable transport stall recovery without parallel subscriptions.
- [x] 4.15 Replace per-revision fixed smoothing with an utterance-local adaptive subtitle reservoir driven by revision cadence and inventory depth.
- [x] 4.16 Tune the subtitle reservoir to a measured 800–1000ms adaptive window and smooth prefix-growing Final tails within 150–250ms while keeping corrective Final authoritative.
- [x] 4.17 Remove presentation buffering and stale shorter-partial retention so every accepted revision renders immediately with longest-common-prefix tail isolation.

## 5. Verification, Evals, and Rollout

- [x] 5.1 Add regression tests for non-blocking ingest, persistent ASR reuse, partial overwrite behavior, and silence/empty-result suppression.
- [x] 5.4 Add regression coverage proving a new interview cannot inherit transcripts, pending questions, or answer tasks from a prior session.
- [x] 5.5 Restrict filler suppression to pure vocal fillers and preserve meaningful short Chinese responses.
- [x] 5.2 Add or update evals / performance checks for TTFT, final transcript latency, dropped-partial policy, and transcript stability under burst traffic.
- [ ] 5.3 Run end-to-end validation with the desktop companion, backend, and web live page; compare against the recorded baseline and document rollout / rollback guidance.
- [x] 5.6 Add regression coverage for ordered incremental desktop revisions and background partial/final provider event delivery.
- [x] 5.7 Remove synchronous per-chunk runtime aggregation from the real-provider latency profiler.
- [x] Persist transcript activity revisions independently from operational events so SSE consumers wake immediately.
- [x] Reduce unhealthy-stream fallback synchronization to one second and stop it after the stream becomes healthy.
- [x] Reject stale publisher tokens with a terminal WebSocket policy close so backend restarts do not cause retry storms or ASGI exception loops.
- [x] 5.8 Preserve the first Qwen audio append timestamp per utterance and calculate provider TTFT from that immutable anchor.
- [x] 5.9 Render each accepted realtime partial revision immediately without a synthetic progressive reveal delay.
- [x] 5.10 Prefer the configured Aliyun Bailian Workspace endpoint, document its safe fallback, and verify endpoint selection without exposing credentials.
- [x] 5.11 Stabilize visible realtime partials against temporary provider retractions while keeping growth immediate and Final authoritative.
- [x] 5.12 Add regressions and complete staged Backend/Web/Desktop validation for the Partial fast path and revision-preserving delivery.
- [x] 5.13 Add regressions proving empty completed utterances do not create ASR reconnect storms.
- [x] 5.14 Add Web regressions for adaptive subtitle pacing, correction/retraction handling, Final authority, session cleanup, and bounded render scheduling.
- [x] 5.15 Add Backend/Web regressions for immediate bootstrap delivery, bootstrap-race event preservation, healthy silent streams, and single-reader transport recovery.
- [x] 5.16 Add Web regressions for regular batched revisions, low/high reservoir inventory, 650ms hard catch-up, correction, Final, reduced-motion, and shared scheduling.
- [x] 5.17 Add Backend regressions for first-error preservation, source isolation, rolling-tail recovery, transcript stitching, continuous task reuse, and compatibility fallback.
- [x] 5.18 Add a regression proving the safe default rolls tasks per utterance without recreating the source WebSocket.
- [x] 5.19 Add regressions proving prewarm does not start an idle task and the next audio frame lazily starts a new task on the existing WebSocket.
- [x] 5.20 Add Web regressions for measured reservoir bounds, low-inventory pacing, prefix-growing Final tails, corrective Final immediacy, and reduced-motion fallback.
- [x] 5.21 Add Web regressions for immediate growth, correction, retraction and Final rendering in both the stream adapter and transcript component.
