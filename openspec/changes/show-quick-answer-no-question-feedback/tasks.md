## 1. Empty quick-answer interaction

- [x] 1.1 Allow desktop and mobile users to trigger quick answer intent when no question is available while retaining busy and read-only protection
- [x] 1.2 Show dedicated missing-interviewer-question feedback without starting an answer request or changing billing state
- [x] 1.3 Clear only the dedicated feedback when manual input or a recognized interviewer question becomes available

## 2. Regression verification

- [x] 2.1 Add component tests for clickable empty quick-answer controls and retained processing-state protection
- [x] 2.2 Add live workspace tests for feedback copy, zero answer requests, unchanged state, and automatic recovery
- [x] 2.3 Run focused Web tests and the production Web build
- [x] 2.4 Validate the OpenSpec change in strict mode and review the final diff
