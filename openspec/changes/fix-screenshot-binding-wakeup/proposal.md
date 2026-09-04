## Why

Companion 1.2.14 can suspend screenshot SSE after a recoverable 404/409 binding race and fail to wake while capture state remains unchanged. A production test waited 65.2 seconds for the Companion to claim an already-created screenshot request even though upload and model processing were healthy, so binding recovery must become authoritative and bounded.

## What Changes

- Drive screenshot-stream ownership from the current `sessionId + bindingId`, rather than only from coarse capture-state transitions or window activation.
- Distinguish device-registration failure from a temporary no-live-binding response and revalidate recoverable bindings without permanent suspension.
- Preserve one stream owner, one in-flight binding check and request idempotency while guaranteeing a bounded wakeup after a valid binding appears.
- Add regression coverage for unchanged `capturing` state, rapid consecutive interviews, duplicate binding notifications, terminal device identity, and retryable transport failures.
- Publish Companion 1.2.15 only after full regression testing and a zero-active-interview production gate.
- Preserve audio capture, ASR, transcripts, answers, prompts, billing, permissions and layout.

## Capabilities

### New Capabilities

- `screenshot-binding-recovery`: Defines binding-identity-driven screenshot SSE ownership, error classification, bounded recovery and duplicate-owner protection.

### Modified Capabilities

None.

## Impact

- Desktop renderer-to-main binding lifecycle notification and main-process screenshot stream state machine.
- Desktop policy/unit/source-contract tests and release packaging.
- Backend API and SSE contracts remain compatible; no production data migration is required.
- No audio, transcript, screenshot content or personal information is added to diagnostics or persistence.
