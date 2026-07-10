## 1. Live workspace layout refinement

- [x] 1.1 Move the session-level `开始面试` and `结束面试` controls into the live page header right-side action area.
- [x] 1.2 Refactor the live workspace so the manual question input sits below the left-side conversation region.
- [x] 1.3 Refactor the live workspace so the right-side answer region owns the `快答` and `截屏回答` action area.
- [x] 1.4 Update narrow-screen layout ordering to `实时对话 -> 手动问题输入 -> 回答 -> 快答/截屏回答`.

## 2. Instant screenshot answer flow

- [x] 2.1 Replace the upload-oriented screenshot trigger in the live page with a user-initiated instant screen capture entry.
- [x] 2.2 Add or adapt a capture adapter boundary so Web and desktop capture implementations can plug into the same screenshot answer flow.
- [x] 2.3 Remove upload-specific intermediate copy and states from the live screenshot path while preserving cancellable and failure recovery states.
- [x] 2.4 Keep screenshot answer submission compatible with the existing Screenshot Answer Service contract after capture completes.

## 3. Verification and regression coverage

- [x] 3.1 Update live workspace tests for the new control placement and left/right bottom action ownership.
- [x] 3.2 Add regression tests for narrow-screen ordering and keyboard-safe visibility of input and action areas.
- [x] 3.3 Add regression tests for instant screenshot trigger, cancellation, and failure recovery without file-upload UI.
- [x] 3.4 Update `ai/evals/` coverage if screenshot-answer behavior or answer-triggering semantics change.
- [x] 3.5 Run `openspec validate refine-live-workspace-and-instant-screenshot --strict`.
