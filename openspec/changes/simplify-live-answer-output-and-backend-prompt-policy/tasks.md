## 1. Answer presentation simplification

- [x] 1.1 Review the current `AnswerWorkspace` rendering path and identify which sections are only prototype-oriented structure versus necessary runtime information.
- [x] 1.2 Refactor the completed-answer UI so the main model answer text becomes the primary content of the right-side answer area.
- [x] 1.3 Demote or remove fixed outline / inference presentation from the primary live answer view while preserving necessary source and status information.

## 2. Backend prompt ownership

- [x] 2.1 Audit the current manual-answer response contract and frontend mapping to remove frontend dependence on answer-structure strategy.
- [x] 2.2 Update the backend chat prompt template and/or prompt builder so answer strategy is maintained in backend prompt assets instead of frontend UI structure.
- [x] 2.3 Ensure the live-answer runtime returns content that can be directly rendered as the main answer body in the frontend.

## 3. Verification

- [x] 3.1 Add regression tests for completed live answers rendering primarily as answer body text.
- [x] 3.2 Add regression tests for history, failure, and generating states after the presentation simplification.
- [x] 3.3 Update `ai/evals/` or prompt-linked coverage for the new backend-owned answer strategy if answer behavior changes.
- [x] 3.4 Run `openspec validate simplify-live-answer-output-and-backend-prompt-policy --strict`.
