## Why

The current production ASR uses the Qwen3 Realtime session protocol, while the newly authorized `qwen-audio-3.0-asr-flash-streaming` model is designed for lower-latency streaming transcription and uses a different DashScope task protocol. OfferSteady needs a protocol-correct, reversible model switch so the user can evaluate the new model without risking an unrecoverable production outage.

## What Changes

- Add a server-side DashScope inference-task WebSocket adapter for `qwen-audio-3.0-asr-flash-streaming` using the public `/api-ws/v1/inference` endpoint that passed live authorization and transcription checks.
- Route realtime ASR through an explicit protocol setting so the new task protocol and the existing Qwen3 Realtime protocol remain independently selectable.
- Translate existing source-scoped PCM frames into `run-task`, binary audio, `result-generated`, and `finish-task` events while preserving partial/final transcript semantics.
- Preserve the existing model and endpoint as a configuration-only rollback path; do not attempt an automatic mid-session provider switch.
- Add privacy-safe provider lifecycle diagnostics and regression coverage without storing PCM or transcript content.
- Switch the test configuration to the new model only after unit, integration, and live synthetic-audio checks pass.

## Capabilities

### New Capabilities

- `qwen-audio-streaming-asr-adapter`: Defines protocol selection, source isolation, partial/final mapping, failure handling, privacy boundaries, and rollback behavior for the Qwen Audio 3 streaming ASR provider.

### Modified Capabilities


## Impact

- Backend ASR dependency wiring, provider gateway implementation, configuration, integration verification, and realtime regression tests.
- Server environment variables for model, endpoint, and protocol selection.
- No desktop protocol, page layout, capture permission, database schema, prompt, or client secret changes.
- Production deployment remains a separate rollout action and must retain the prior model configuration for rollback.
