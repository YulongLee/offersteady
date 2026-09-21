## Why

The live interview quick-answer and detailed-answer stages need to move to `deepseek-v4.1-flash` without changing document processing or unrelated AI capabilities. Dedicated stage settings let OfferSteady evaluate and roll back the two live-answer stages independently from the shared chat model.

## What Changes

- Add server-only quick-answer and detailed-answer model settings that each default to the existing shared chat model when not configured.
- Route quick-answer generation, normalization, and quick continuation through the dedicated quick model.
- Route detailed-answer generation and detailed continuation through the dedicated detail model, while summaries, screenshots, and unrelated AI capabilities keep their existing model selection.
- Repeat the existing normalized-question output protocol at the end of the quick user request so the candidate model preserves the machine-readable stream boundary.
- Configure both live-answer stages locally for `deepseek-v4.1-flash` and verify provider compatibility, response structure, output quality, grounding, language behavior, continuity, and latency with synthetic prompts.
- Preserve prompts, billing, retrieval, language routing, streaming order, privacy boundaries, and public API shapes.

## Capabilities

### New Capabilities

- `quick-answer-model-routing`: Selects and verifies independently configurable models for the live quick-answer and detailed-answer stages with backward-compatible fallbacks.

### Modified Capabilities

None.

## Impact

- Backend settings, chat-provider routing, usage telemetry, and integration verification.
- Environment-variable examples and runtime documentation.
- Backend regression tests and privacy-safe AI evaluation cases.
- No client-side secret, database migration, public API change, or production deployment in this change.
