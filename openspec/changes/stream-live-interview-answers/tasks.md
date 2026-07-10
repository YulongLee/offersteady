## 1. Streaming Contract

- [x] 1.1 Define live-answer stream event types for task-started, chunk, completed, failed, and cancelled.
- [x] 1.2 Add backend response schemas or typed payload helpers for safe streaming events.
- [x] 1.3 Add frontend event parsing types that map stream events into answer task and question state.

## 2. Backend Streaming Runtime

- [x] 2.1 Add an SSE or equivalent streaming live-answer endpoint while keeping the existing non-streaming response available.
- [x] 2.2 Update Chat Service / gateway boundaries so answer chunks can be yielded incrementally when stream mode is requested.
- [x] 2.3 Persist task state, chunks, final answer text, usage, failure, and cancellation consistently with existing live-answer history.
- [x] 2.4 Ensure cancellation stops visible output and isolates late provider chunks from completed answers.
- [x] 2.5 Add backend tests for ordered stream events, completion, failure after partial output, and cancellation.

## 3. Frontend Streaming Consumption

- [x] 3.1 Update the backend adapter to submit manual questions through the streaming path when available.
- [x] 3.2 Update live interview state handling so the first chunk appears immediately in the answer area.
- [x] 3.3 Append additional chunks by task id and sequence without duplicating text.
- [x] 3.4 Preserve history viewing, latest-answer notice, retry, and stop-answer behavior while a latest answer streams.
- [x] 3.5 Keep the existing page layout unchanged.

## 4. Verification

- [x] 4.1 Add frontend tests for first chunk rendering, chunk append, completion, failure, cancellation, and history viewing during streaming.
- [x] 4.2 Add or update AI eval coverage for streamed answer completion and partial-failure behavior.
- [x] 4.3 Run backend tests covering live-answer streaming.
- [x] 4.4 Run focused Web tests and Web typecheck.
- [x] 4.5 Run `openspec validate stream-live-interview-answers --strict`.
