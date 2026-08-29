## 1. Quiet live answer actions

- [x] 1.1 Keep the quick-answer and screenshot-answer labels stable while preserving busy-state duplicate-submit protection.
- [x] 1.2 Remove the visible quick-answer and screenshot-answer status row from the live action area on desktop and mobile.

## 2. Regression verification

- [x] 2.1 Add focused component tests proving processing and success states do not render status copy while actions remain protected.
- [x] 2.2 Run the relevant Web tests and production build.
- [x] 2.3 Validate `hide-live-answer-action-status` with OpenSpec strict validation.
