## 1. End-to-End Diagnosis Baseline

- [x] 1.1 Inventory the current live conversation path across desktop capture, desktop transport, backend ingest, backend worker, provider gateway, event publish, frontend subscribe, and frontend render.
- [x] 1.2 Add a shared staged latency model and trace identifiers so one live utterance can be measured across the full chain without storing raw audio.
- [x] 1.3 Capture a real local baseline for candidate and interviewer sources, including first-partial latency, final latency, queue waits, render delay, and dominant bottleneck classification.

## 2. Desktop Capture and Delivery Optimization

- [x] 2.1 Verify that microphone and system-audio capture produce continuous incremental PCM frames after interview binding, and expose delivery counters per source.
- [x] 2.2 Remove any cumulative resend behavior, oversized chunking, or source reinitialization that can delay first partial results.
- [x] 2.3 Add bounded desktop-side buffering, send-health diagnostics, and backlog indicators so the desktop companion can prove whether it is really feeding the backend in real time.

## 3. Backend Realtime Pipeline Optimization

- [x] 3.1 Instrument ingest, queue wait, worker processing, provider append, provider partial, provider final, and transcript publish timings per source.
- [x] 3.2 Optimize the hot path to use persistent per-source provider sessions, bounded asynchronous queues, and stale-partial suppression without changing the public API shape.
- [x] 3.3 Emit explicit anomaly reasons for desktop-no-audio, ingest backlog, provider partial timeout, provider final timeout, publish lag, and subscription lag.

## 4. Web Live Conversation Rendering Optimization

- [x] 4.1 Update the live conversation panel to render partial transcripts immediately, reconcile them with final transcripts, and avoid duplicate rows or whole-sentence late refreshes.
- [x] 4.2 Replace generic waiting copy with chain-aware runtime notices that reflect the actual failing or delayed stage.
- [x] 4.3 Measure frontend receive-to-paint latency and reduce unnecessary re-render or batching delays that hide already-available transcripts.

## 5. Verification and Acceptance

- [x] 5.1 Add regression tests for staged latency tracing, bottleneck classification, partial/final reconciliation, and stale-partial suppression.
- [x] 5.2 Run local end-to-end validation with the desktop companion, backend, and live interview page using the current ASR provider configuration from `.env`.
- [x] 5.3 Record before/after latency measurements, summarize the dominant bottlenecks, and confirm whether the optimized path meets the target of near-real-time visible subtitles.
