## Context

The Qwen-compatible chat gateway historically read one `chat_qwen_model` value for quick answers, detailed answers, continuation calls, non-streaming chat, document summaries, and integration verification. The quick-answer stage has a distinct latency and output contract, while the detailed-answer stage has a larger token budget and retrieval context. The requested upgrade therefore needs two independent, server-only live-answer routing boundaries rather than replacing the shared model value used by unrelated AI capabilities.

Alibaba Cloud Model Studio documents `deepseek-v4.1-flash` as available through the OpenAI-compatible Chat Completions API in both the China (Beijing) and Singapore scopes. The current gateway already sends `enable_thinking=false`, which preserves the low-latency non-thinking behavior required by quick answer.

## Goals / Non-Goals

**Goals:**

- Route quick-answer generation, language repair, and quick-stage continuation through a dedicated configurable model.
- Route detailed-answer generation, language repair, and detail-stage continuation through a dedicated configurable model.
- Default each stage safely to `chat_qwen_model` when its dedicated model is not configured.
- Record the actual selected model in provider logs and gateway results.
- Verify request compatibility, normalization, answer quality, grounding, language routing, quick/detail continuity, streaming, and latency using synthetic inputs.

**Non-Goals:**

- Do not change screenshot, document-summary, generic non-live chat, embedding, rerank, or ASR model selection.
- Do not change prompts, retrieval, token budgets, billing, public request/response shapes, or production deployment configuration.
- Do not introduce client-visible model selection or expose provider credentials.

## Decisions

### Select both live-answer models from the server-side prompt stage

The gateway resolves the dedicated quick model when the versioned prompt template identifies the quick stage, including quick-stage continuations. It resolves the dedicated detail model for detail prompts and detail-stage continuations. Prompt templates without either live-answer stage continue to use `chat_qwen_model`.

Alternative: add a model argument to every gateway call. Rejected because prompt stage already provides the authoritative routing signal and widening the port would touch every test adapter without adding product value.

### Preserve a backward-compatible configuration fallback

`OFFERSTEADY_CHAT_QUICK_MODEL` and `OFFERSTEADY_CHAT_DETAIL_MODEL` will be optional. Empty or missing stage configuration resolves to `OFFERSTEADY_CHAT_QWEN_MODEL`, so existing deployments retain their current behavior until explicitly enabled.

Alternative: change `OFFERSTEADY_CHAT_QWEN_MODEL` directly. Rejected because that would also replace document summaries and generic non-live chat, exceeding the requested scope.

### Verify the candidate without production deployment

The local provider probes will send synthetic interview questions through both stages using the same Chat Completions endpoint, non-thinking mode, stage-specific token budgets, normalized-question envelope, quick anchor, and retrieval context expected by the live path. Regression tests will assert routing and telemetry without relying on real user data.

Alternative: deploy directly and compare production telemetry. Rejected because model compatibility and behavior can be validated locally before any user traffic is exposed.

### Reinforce the existing quick output protocol at the final instruction boundary

The versioned quick system prompt remains authoritative. The prompt builder also repeats the exact normalized-question tag contract at the end of the quick user request because provider testing showed that `deepseek-v4.1-flash` otherwise produced a useful answer but omitted the required XML envelope. The reminder adds no new facts or answer-policy instruction and is excluded from detail prompts.

Alternative: accept the raw question fallback for every candidate-model response. Rejected because it would silently remove the existing question-normalization behavior and weaken visible question quality.

## Risks / Trade-offs

- [The new model emits a different normalization envelope] → Repeat the existing protocol at the final quick instruction boundary, exercise the actual provider with a synthetic prompt, and retain fallback parsing tests.
- [Quick and detailed answers diverge] → Keep the quick answer as the authoritative anchor in the unchanged detailed prompt and run the quick/detail consistency eval.
- [Misconfiguration causes one live-answer stage to fail] → Fall back to the shared model when that stage's dedicated setting is absent; surface existing structured provider errors when an explicitly configured model is invalid.
- [Latency varies by provider load] → Record multiple warm synthetic samples and report median/range without treating a single sample as a production guarantee.

## Migration Plan

1. Add the optional quick/detail settings, routing tests, evaluation fixture, and documentation.
2. Run focused backend tests, prompt/eval regressions, and strict OpenSpec validation.
3. Run authenticated synthetic quick and detailed provider probes locally with `deepseek-v4.1-flash`.
4. Keep production unchanged until a separate deployment request; rollback is removing the affected stage override or setting it back to the shared model.

## Open Questions

None for local validation. Production enablement remains a separate user-approved action.
