## 1. Regression Coverage

- [x] 1.1 Add a backend regression test for system partial → microphone final → system final ordering and verify one interviewer answer is triggered.
- [x] 1.2 Add a backend regression test proving a suppressed final closes its existing partial without context, answer, or billing side effects.
- [x] 1.3 Add a web regression test for the bounded stale-partial presentation guard.

## 2. Backend Finalization Recovery

- [x] 2.1 Make cross-channel deduplication prefer system-audio finals over microphone echoes.
- [x] 2.2 Reconcile an existing same-segment partial into a terminal display record when its final is intentionally suppressed.

## 3. Web Recovery Presentation

- [x] 3.1 Stop the active caret and show “识别未完成” after a partial transcript becomes stale while preserving provider-final semantics.

## 4. Verification

- [x] 4.1 Run focused backend and web regression tests for transcript finalization, question detection, and conversation rendering.
- [x] 4.2 Run the broader backend and web test/build checks affected by the change.
- [x] 4.3 Validate the OpenSpec change strictly and review the final diff for unrelated modifications.
