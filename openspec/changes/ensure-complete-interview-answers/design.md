## Context

`stream_answer_question` generates a quick stage and a detail stage. The Qwen-compatible adapter currently emits only text chunks, discards `choices[0].finish_reason`, and uses a fixed 520-token limit. After both iterators finish, the service constructs a synthetic `finish_reason="completed"` and persists the task as completed without checking either stage.

## Goals / Non-Goals

**Goals**

- Detect provider length termination for both answer stages.
- Automatically continue only the incomplete stage while preserving visible output.
- Keep continuation bounded, deterministic, cancellable, and observable.
- Never report an incomplete answer as completed.

**Non-Goals**

- Changing model provider, retrieval, billing, question normalization, or speaker detection.
- Guaranteeing a particular word count when a shorter answer is already semantically complete.
- Sending source material or provider payloads to the browser.

## Decisions

### Preserve safe provider completion metadata on stream chunks

The gateway attaches a normalized finish reason to the terminal stream chunk. `stop` is normal completion; `length` is incomplete; other provider termination reasons fail safely. This keeps metadata request-local and concurrency-safe.

### Use stage-specific output budgets

Quick answers receive a bounded concise budget while detailed answers receive a larger budget. Configuration remains server-side and defaults are sufficient for normal interview answers.

### Continue the incomplete stage with a dedicated prompt

A continuation prompt in `ai/prompts/chat-service/continuation.md` receives the already-generated stage text as an authoritative prefix and asks for only the missing suffix. The service appends the suffix through a longest-overlap merge so providers that repeat the ending cannot duplicate visible text.

### Require a trustworthy terminal state

Length termination always requires continuation. A normal stop is accepted unless the visible stage has an unmatched code fence or ends with an unmistakably unfinished delimiter such as a comma, colon, semicolon, opening bracket, or dangling list marker. Continuation is bounded; exhaustion raises a safe incomplete-answer error while preserving partial text.

## Risks / Trade-offs

- A provider may omit a finish reason. The adapter treats a completed stream without a reason as normal for compatibility, then applies the obvious-incompleteness check.
- Heuristics can be over-eager. They intentionally cover only strong syntactic signals and provider length termination.
- Continuation adds latency and tokens only on incomplete stages. A strict attempt cap prevents unbounded spend.

## Migration / Rollback

The change is backward-compatible with existing gateways that emit no finish reason. Rollback restores the prior fixed budgets and single-pass stream behavior; no data migration is required.
