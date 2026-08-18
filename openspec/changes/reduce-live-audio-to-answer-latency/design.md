## Context

The production path is Electron audio capture → multiplexed WebSocket ingest → persistent realtime ASR → realtime repository/SSE → React. System audio partials are emitted every 100 ms, but a final waits 650 ms of silence (microphone: 850 ms). The web then coalesces one SSE snapshot through two animation frames and reveals active transcript text at two characters per 32 ms. For a high-confidence interviewer question, `RealtimeSpeechService` invokes the synchronous `ChatService.answer_question` on the source worker; the provider must complete before the answer task is linked and exposed.

The existing manual-question SSE endpoint is genuinely streamed, but it uses the manual quick-plus-detail prompt flow. Automatic interviewer answers must retain their current single-answer prompt, retrieval, billing, history, cancellation, and content semantics.

## Goals / Non-Goals

**Goals:**

- Keep the realtime audio worker free after final transcript/question publication.
- Preserve the existing automatic answer prompt and commercial behavior while exposing its first provider chunks immediately.
- Make already-received partial transcript revisions visibly catch up within a small bounded render budget.
- Reduce silence finalization conservatively and retain existing segment assembly/deduplication.
- Add regression and latency evidence for the automatic path.

**Non-Goals:**

- No model, ASR provider, public page layout, speaker-role, pricing, or material-selection changes.
- No raw-audio persistence or production database migration.
- No rewrite of the existing manual quick-plus-detail stream.
- No attempt to claim physical-device or meeting-platform latency from synthetic tests.

## Decisions

### Add a dedicated automatic-answer stream in Chat Service

Add a generator dedicated to automatically confirmed interviewer questions. It will reuse the current automatic system prompt, conversation history, retrieval/material context, task persistence, usage accounting, and billing lifecycle, but consume `LLMGatewayPort.stream_generate` and persist each ordered chunk. This avoids changing automatic answer structure to the manual quick-plus-detail format.

Alternative considered: call the existing manual `stream_answer_question`. Rejected because that would change visible answer structure and prompt behavior.

### Run automatic generation outside the audio source worker

After saving the final transcript and confirmed candidate, submit automatic generation to a bounded answer executor. Stream progress is mirrored into realtime events with a compact task snapshot so the existing session SSE delivers it without frontend polling. Candidate/task identity is linked as soon as the stream creates the task.

Alternative considered: make the browser start the automatic answer. Rejected because generation would depend on one page remaining connected and could duplicate billing after reconnects.

### Reconcile streamed automatic answers through existing workspace state

Extend realtime session updates with an optional automatic-answer result derived from the latest answer stream event. The live page will reuse existing answer workspace reconciliation; no new panel or control is introduced. Ordered task snapshots make reconnects idempotent.

### Replace fixed two-character transcript animation with adaptive catch-up

Active transcripts will reveal a bounded proportion of the remaining text on each frame, with a minimum chunk large enough to catch up promptly. Final transcripts remain immediate. This preserves the progressive visual cue without allowing the animation to trail backend state for seconds.

### Tune silence windows conservatively

Use 500 ms for system audio and 700 ms for microphone audio. Existing question-turn assembly and duplicate suppression remain authoritative when a natural pause creates multiple segments.

### Keep SSE transport and public routes stable

The current 100 ms idle cursor check and proxy buffering protections remain. This change optimizes the dominant waits first; replacing repository cursor polling with a pub/sub primitive is deferred to avoid architecture expansion.

## Risks / Trade-offs

- [Shorter silence windows can create more final segments] → Keep conservative thresholds and verify adjacent interviewer segments still assemble into one question without duplicate answers.
- [Background answer threads can outlive ended sessions] → Bound executor concurrency, check task cancellation/session state, and isolate late chunks from completed/cancelled tasks.
- [Realtime progress events increase event volume] → Emit compact snapshots and coalesce/throttle progress events while always emitting start and terminal states.
- [Provider streaming output can differ slightly from non-streaming output] → Keep the same prompt/model/temperature configuration and validate answer completeness/evals.
- [Frontend reconnect can replay older progress] → Reconcile by task id, revision/update time, and terminal-state precedence.

## Migration Plan

1. Deploy backend support and compatibility tests first within the same release image.
2. Deploy the web reconciliation and desktop silence tuning together.
3. Validate synthetic audio, automatic answer first chunk, cancellation, reconnect, billing, and history before production rollout.
4. Roll back the release image if automatic answer failures or duplicate billing increase; no data migration is required.

## Open Questions

None. The scope and acceptance criteria are fixed by the current production behavior and measured latency baseline.
