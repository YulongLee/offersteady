## 1. State Diagnosis and Regression Coverage

- [x] 1.1 Add synthetic unit tests for answer-task ordering, monotonic lifecycle transitions, and stale/shorter stream updates.
- [x] 1.2 Add focused live-workspace component tests for newest-answer ownership, history viewing, quick-answer feedback, and screenshot staged feedback.
- [x] 1.3 Add or update backend tests for complete final system questions, uncertain candidates, and the no-automatic-answer boundary.
- [x] 1.4 Add a regression test for an older same-task workspace snapshot arriving between streamed answer updates.
- [x] 1.5 Add regressions for screenshot completion racing with an older answer event and terminal screenshot state receiving a stale processing event.

## 2. Deterministic Live Answer State

- [x] 2.1 Implement a shared deterministic merge helper for questions and answer tasks using identity, revision, lifecycle stage, update time, and explicit local ownership.
- [x] 2.2 Replace workspace refresh, streaming callback, and assistant-shortcut merge paths so late events can enrich history but cannot replace a newer current task or shorten its text.
- [x] 2.3 Make explicit quick, manual, and screenshot actions immediately select their placeholder/current answer while preserving history navigation.
- [x] 2.4 Keep same-task question text monotonic when polling and streaming updates race at the same revision.
- [x] 2.5 Merge simultaneous screenshot and speech-answer updates without losing either result, and prevent a completed screenshot request from returning to processing.

## 3. Smooth Rendering and Action Feedback

- [x] 3.1 Batch small streamed-answer visual updates and immediately flush terminal events without clearing already visible content.
- [x] 3.2 Update answer-section rendering so placeholders do not flash or remain after a terminal answer with no detailed section.
- [x] 3.3 Give quick-answer and screenshot-answer buttons clear ready, processing, success, failure, cancellation, disabled, and accessible live-status states.
- [x] 3.4 Keep question-normalization metadata internal so its pending/completed transition cannot shift the visible answer layout.
- [x] 3.5 Isolate answer-body rendering from unrelated realtime updates and defer full Markdown parsing until stream completion.
- [x] 3.6 Keep desktop and mobile screenshot-action labels stable while retaining disabled duplicate protection and separate accessible progress feedback.

## 4. Explicit Answer Triggering

- [x] 4.1 Keep realtime speech responsible for transcripts and question candidates without starting answer generation.
- [x] 4.2 Require quick answer or screenshot answer to explicitly start generation and preserve idempotency for duplicate actions.
- [x] 4.3 Remove automatic answer creation from realtime detection and candidate confirmation, then add backend regression coverage.

## 5. Verification and Release

- [x] 5.1 Run focused Web and Backend regressions, type checks, production builds, and strict OpenSpec validation with synthetic fixtures only.
- [ ] 5.2 Perform a local browser smoke test for no answer before user action, quick answer, screenshot answer, stream completion, history navigation, stop, failure, and retry states.
- [x] 5.3 Review the diff for privacy and unrelated behavior, commit and push the approved scope to Git.
- [x] 5.4 Deploy only affected services without restarting PostgreSQL, Redis, or unrelated services, then verify production health and key live-workspace behavior.
