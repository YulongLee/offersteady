## 1. Baseline and Performance Instrumentation

- [x] 1.1 Add stage-level timing probes for capture, queue wait, ASR TTFT, final transcript latency, backend push, and frontend render latency.
- [x] 1.2 Add runtime counters for queue depth, dropped partial updates, connection recreations, CPU-sensitive allocation hotspots, and empty/phantom transcript suppression.
- [x] 1.3 Build a reproducible local performance benchmark flow and record the current baseline before refactoring.

## 2. Desktop Audio Pipeline Refactor

- [x] 2.1 Replace cumulative utterance payload generation with incremental PCM chunk streaming per source.
- [x] 2.2 Introduce source-scoped bounded buffering (RingBuffer or equivalent) and freshness-first backpressure rules for microphone and system audio.
- [ ] 2.3 Migrate capture callbacks toward AudioWorklet/native-producer-friendly boundaries and keep ScriptProcessor only as a fallback path.
- [ ] 2.4 Recalibrate silence gating and empty-audio suppression separately for source health, utterance start, and transcript publish eligibility.

## 3. Backend Realtime ASR Pipeline Refactor

- [x] 3.1 Decouple ingest from transcription so audio receive paths return quickly after enqueueing work.
- [x] 3.2 Introduce persistent ASR sessions per `sessionId + sourceKind` with long-lived streaming workers.
- [x] 3.3 Implement source-local producer-consumer workers that send incremental audio, reconcile partial/final transcript events, and avoid synchronous request blocking.
- [x] 3.4 Add worker lifecycle, idle timeout, error recovery, and rollback-safe feature flags for the new pipeline.

## 4. Web Transcript Streaming and Overlay Efficiency

- [x] 4.1 Refactor live conversation state to reconcile partial and final transcripts by stable utterance identity instead of appending duplicate rows.
- [x] 4.2 Minimize UI update cost with incremental state updates, batching, and suppression of empty/phantom transcript renders.
- [x] 4.3 Preserve the current live workspace layout while updating diagnostics to reflect source-specific realtime latency and degradation states.
- [x] 4.4 Assemble the latest interviewer turn for quick answer, including a newer partial revision without mixing candidate speech into the question.

## 5. Verification, Evals, and Rollout

- [x] 5.1 Add regression tests for non-blocking ingest, persistent ASR reuse, partial overwrite behavior, and silence/empty-result suppression.
- [ ] 5.2 Add or update evals / performance checks for TTFT, final transcript latency, dropped-partial policy, and transcript stability under burst traffic.
- [ ] 5.3 Run end-to-end validation with the desktop companion, backend, and web live page; compare against the recorded baseline and document rollout / rollback guidance.
