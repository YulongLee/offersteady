## 1. Contract and prompt

- [x] 1.1 Preserve normalized provider finish reasons on streamed gateway chunks and add stage-specific server configuration.
- [x] 1.2 Add a centralized continuation prompt and synthetic AI eval cases for quick and detailed truncation.

## 2. Complete answer runtime

- [x] 2.1 Implement strong incomplete-answer detection, overlap-safe suffix merging, and bounded stage continuation.
- [x] 2.2 Apply the completion guard independently to quick and detail stages while preserving cancellation, ordered chunks, partial failure, usage, and billing behavior.
- [x] 2.3 Add privacy-safe structural logging for finish reasons and continuation attempts.

## 3. Regression verification

- [x] 3.1 Add backend gateway tests for stop, length, missing finish reason, and stage token budgets.
- [x] 3.2 Add service regressions proving quick/detail continuation completes without duplication and exhaustion never emits completed.
- [x] 3.3 Run focused backend tests, AI eval validation, backend type/lint checks available in the repository, and strict OpenSpec validation.
- [x] 3.4 Review the final diff for privacy, API compatibility, and unrelated changes.
