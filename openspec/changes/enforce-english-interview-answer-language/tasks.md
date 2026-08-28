## 1. Prompt Language Contract

- [x] 1.1 Strengthen every English chat and screenshot prompt asset with an English-only output contract that applies even to Chinese questions, titles, history, screenshots, and evidence.
- [x] 1.2 Add authoritative output-language blocks to chat and screenshot prompt builders while preserving source evidence verbatim and leaving Chinese prompts byte-for-byte unchanged.

## 2. Provider Output Enforcement

- [x] 2.1 Add a deterministic, content-free material-Chinese detector with proper-noun tolerance and focused unit tests.
- [x] 2.2 Enforce English output for non-streaming, quick, detail, continuation, screenshot, and fallback completion paths; perform one bounded repair retry and fail closed on repeated drift.
- [x] 2.3 Add structured language-violation telemetry that records language, stage, template/version, attempt, and stable code without content.

## 3. English Answer Surface

- [x] 3.1 Make answer-section parsing recognize English headings and render English quick/detail framing for `en-US` sessions without introducing full application localization.
- [x] 3.2 Add Web regression tests for English answer parsing/labels and unchanged Chinese labels.

## 4. Regression And Evaluation

- [x] 4.1 Add backend provider-shaped tests using Chinese questions, titles, and materials in English sessions, covering repair success, repeated-drift failure, streaming stages, screenshots, proper nouns, and Chinese compatibility.
- [x] 4.2 Add synthetic AI eval cases and assertions for English output with Chinese/mixed-language evidence.
- [x] 4.3 Run focused and full relevant Backend/Web tests, AI evals, builds, `git diff --check`, and `openspec validate enforce-english-interview-answer-language --strict`; record exact results.

## 5. Release Verification

- [x] 5.1 Verify a real configured provider call with synthetic Chinese input/evidence returns English quick/detail output without logging content or credentials.
- [x] 5.2 Confirm no desktop code or protocol change is required, then document deployment and rollback scope for Backend/Web only.
