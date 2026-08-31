## Why

Production traces show that the answer provider usually returns its first raw token in about one second, while the server still spends repeated synchronous database and connection setup work before the request reaches the provider. The product needs a safer low-latency startup path that preserves billing, grounding, normalization, cancellation, recovery, and answer quality.

## What Changes

- Reuse one validated interview-session snapshot while admitting and preparing a live quick answer instead of repeatedly refreshing the same session and bound documents.
- Avoid redundant activity and context persistence work on the first-visible-answer critical path while preserving durable question history and session activity semantics.
- Reuse a bounded server-side HTTP connection pool for Qwen-compatible chat streaming instead of creating a new client for each quick and detail request.
- Record privacy-safe stage timings from browser intent through provider request, first raw token, first visible answer event, and browser render acknowledgement.
- Add regression and synthetic performance coverage for billing idempotency, selected-material grounding, normalization, English output, cancellation, history, and streaming order.
- Roll out only the behavior-preserving optimizations in this change; answer-first protocol changes, model replacement, prompt changes, layout changes, and multi-worker deployment are excluded.

## Capabilities

### New Capabilities

- `low-latency-live-answer-startup`: Starts a manual live answer with bounded duplicate storage work, reusable provider connections, and measurable first-visible-answer latency while retaining existing product behavior.

### Modified Capabilities

None.

## Impact

- Backend chat, interview-session, telemetry, and dependency lifecycle code.
- Web live-answer stream timing acknowledgement.
- Backend and web regression tests plus synthetic performance tests.
- No public request shape removal, no model or prompt change, no new client credential, and no persistence of question or answer content in telemetry.
