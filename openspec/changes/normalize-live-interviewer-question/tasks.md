## 1. Backend question contract

- [x] 1.1 Extend live-answer task records and API responses with raw question, normalized question, and normalization status.
- [x] 1.2 Add a bounded parser for the quick-model normalization envelope with safe raw-question fallback.
- [x] 1.3 Emit a question-normalized stream update and use the normalized question for detailed answer and RAG.

## 2. Prompt and Web experience

- [x] 2.1 Update the quick-answer prompt to organize fragmented speech without changing interviewer intent.
- [x] 2.2 Map normalization fields through the Web adapter and display the organized question above the answer.
- [x] 2.3 Preserve compatibility for legacy tasks and manual/screenshot question records.

## 3. Tests and evaluation

- [x] 3.1 Add backend regression tests for valid, malformed, and fallback normalization output.
- [x] 3.2 Add Web streaming tests for updating the visible question before answer completion.
- [x] 3.3 Add synthetic AI evaluation cases for fragmented, repeated, referential, and multi-part questions.
- [x] 3.4 Run focused backend/Web tests, production build, and strict OpenSpec validation.
