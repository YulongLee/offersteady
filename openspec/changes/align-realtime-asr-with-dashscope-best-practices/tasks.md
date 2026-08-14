## 1. Provider Gateway Alignment

- [x] 1.1 Review the current DashScope realtime ASR gateway against the official recommended event flow and document the mismatches.
- [x] 1.2 Refactor the gateway to prefer the Alibaba Bailian workspace-specific realtime endpoint and to wait for provider-ready state before sending `session.update`.
- [x] 1.3 Refactor the gateway to use a source-scoped persistent realtime session with one-time session initialization and incremental append / commit handling.
- [x] 1.4 Split provider event handling into partial transcript updates, final transcript completion, VAD/Manual mode state, and structured provider error classification.

## 2. Backend Realtime Orchestration

- [x] 2.1 Decouple frame ingest from synchronous transcription so provider streaming runs in a background source worker.
- [x] 2.2 Add source-scoped worker lifecycle management, session reuse, idle timeout, reconnection handling, and provider-ready/session-created gating for DashScope realtime sessions.
- [x] 2.3 Preserve current runtime and transcript APIs while upgrading their internals to publish provider-aware partial / final updates and VAD/Manual mode diagnostics.

## 3. Desktop Audio Delivery

- [x] 3.1 Replace cumulative utterance retransmission with incremental PCM chunk delivery that matches the provider worker expectations.
- [x] 3.2 Align utterance boundary and silence gating with provider VAD / Manual commit behavior to reduce blank or phantom partials.
- [x] 3.3 Expose source health and delivery diagnostics needed to confirm microphone and system-audio frames are actually entering the provider pipeline.
- [x] 3.4 Preserve bounded unacknowledged audio across reconnects, refresh invalid publisher credentials once, and report explicit sequence gaps on overflow.
- [x] 3.5 Add adaptive per-source silence gating and move capture processing to AudioWorklet with a compatibility fallback.

## 4. Web Live Transcript Consumption

- [x] 4.1 Update realtime conversation rendering to reconcile provider partial and final transcript states without duplicate rows or delayed whole-sentence refreshes.
- [x] 4.2 Keep the current live workspace layout unchanged while surfacing provider-aware runtime notices for missing audio, provider failure, or delayed finalization.

## 5. Verification and Evals

- [x] 5.1 Add backend regression tests for persistent provider session reuse, `session.created → session.update → append / commit` sequencing, partial overwrite behavior, and final-only context persistence.
- [x] 5.2 Add or update evals / performance checks for TTFT, partial continuity, blank-result suppression, provider reconnection handling, and VAD-to-Manual fallback behavior.
- [x] 5.3 Run local end-to-end validation with the desktop companion, backend, and live interview page, then record baseline versus improved provider-path results.
- [ ] 5.4 Run targeted and full regression/build gates, verify unrelated interview, answer, screenshot, billing, and material workflows remain unchanged, and record deployment smoke results.
