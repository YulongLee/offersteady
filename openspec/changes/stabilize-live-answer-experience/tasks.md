## 1. State Diagnosis and Regression Coverage

- [x] 1.1 Add synthetic unit tests for answer-task ordering, monotonic lifecycle transitions, and stale/shorter stream updates.
- [x] 1.2 Add focused live-workspace component tests for newest-answer ownership, history viewing, quick-answer feedback, and screenshot staged feedback.
- [x] 1.3 Add or update backend tests for complete final system questions, uncertain candidates, and duplicate automatic-answer events.

## 2. Deterministic Live Answer State

- [x] 2.1 Implement a shared deterministic merge helper for questions and answer tasks using identity, revision, lifecycle stage, update time, and explicit local ownership.
- [x] 2.2 Replace workspace refresh, streaming callback, and assistant-shortcut merge paths so late events can enrich history but cannot replace a newer current task or shorten its text.
- [x] 2.3 Make explicit quick, manual, and screenshot actions immediately select their placeholder/current answer while preserving intentional history viewing for passive automatic answers.

## 3. Smooth Rendering and Action Feedback

- [x] 3.1 Batch small streamed-answer visual updates and immediately flush terminal events without clearing already visible content.
- [x] 3.2 Update answer-section rendering so placeholders do not flash or remain after a terminal answer with no detailed section.
- [x] 3.3 Give quick-answer and screenshot-answer buttons clear ready, processing, success, failure, cancellation, disabled, and accessible live-status states.

## 4. Automatic Question Answering

- [x] 4.1 Verify and correct the automatic confirmation rule so final, complete, high-confidence system questions trigger exactly one answer without relying on punctuation.
- [x] 4.2 Preserve manual confirmation for non-final, incomplete, conflicting, or low-confidence candidates and ensure duplicate events are idempotent.

## 5. Verification and Release

- [x] 5.1 Run focused Web and Backend regressions, type checks, production builds, and strict OpenSpec validation with synthetic fixtures only.
- [ ] 5.2 Perform a local browser smoke test for automatic answer, quick answer, screenshot answer, stream completion, history navigation, stop, failure, and retry states.
- [x] 5.3 Review the diff for privacy and unrelated behavior, commit and push the approved scope to Git.
- [x] 5.4 Deploy only affected services without restarting PostgreSQL, Redis, or unrelated services, then verify production health and key live-workspace behavior.
