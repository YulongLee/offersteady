## Context

The authoritative session language and English prompt resolver are already working: an `en-US` stream receives the English quick/detail headings and English template IDs. Production evidence nevertheless shows a Chinese answer body when the question, title, and fixed materials are Chinese. Qwen follows the dominant language of the evidence despite the single English instruction. Existing integration tests use the deterministic local gateway, whose English output is selected directly from the template ID, so they cannot reproduce provider language drift.

The answer path is staged and streamed. Quick output is already buffered until the normalized-question envelope closes, while detail output is currently forwarded chunk by chunk. Any guard must preserve useful streaming latency, avoid translating or persisting user evidence, and leave Chinese sessions unchanged.

## Goals / Non-Goals

**Goals:**

- Keep normalized questions, quick answers, detail answers, continuations, screenshot answers, and fallbacks in English for every `en-US` session.
- Handle Chinese questions and Chinese evidence without treating their language as the requested output language.
- Prevent a materially Chinese provider response from being marked completed as an English answer.
- Preserve the current Chinese path and content-free diagnostics.

**Non-Goals:**

- Full English localization of navigation, billing, settings, and all live-workspace status text.
- Automatic per-turn language detection or changing the authoritative session language.
- Persisting translated copies of resumes, JD, knowledge, transcripts, or screenshots.
- Changing the desktop audio protocol or ASR provider.

## Decisions

### 1. Repeat a structured output-language contract at both prompt priorities

Every English system/stage template will explicitly state that all generated natural-language text must be English even when the question, title, history, screenshot, or evidence is Chinese. The prompt builders will also add a compact authoritative `<output_language>` block next to the current request. This intentionally repeats the contract in the system and user messages because real provider behavior shows that a system-only instruction loses against a predominantly Chinese context.

Runtime translation of the Chinese template was rejected because it adds latency, weakens versioning, and can alter evidence. The original evidence remains unchanged inside untrusted evidence blocks; only generated output is constrained.

### 2. Validate provider output rather than trusting template selection

The backend will use a deterministic script-balance check for `en-US` output. A response is materially non-English when it contains at least four Han characters and Han characters exceed a small share of its alphabetic/Han content. This permits an occasional verified Chinese proper noun inside an otherwise English response but rejects examples such as `介绍自己` and Chinese answer paragraphs.

Quick streaming is checked before its existing normalization buffer is released, so a bad first attempt is never shown. Non-streaming and completed detail/continuation outputs are checked before success. Detail streaming receives an initial language buffer before release and remains guarded at completion. A violation uses a content-free error code and does not log the text.

### 3. Use one bounded English-repair retry, then fail closed

On a language violation, the existing retry budget performs a second provider call with an additional English-only repair directive. The retry receives the original evidence, not the Chinese answer, so it cannot silently turn unsupported statements into facts. If the second output still violates the language contract, the task fails safely instead of publishing Chinese as a successful English answer.

Unlimited retries and a separate translation model were rejected because both add uncontrolled latency and cost. The retry is only triggered on a deterministic language violation.

### 4. Keep answer-surface parsing bilingual

The Web answer parser will recognize both Chinese and English generated headings. When the current session is English, the quick/detail section labels that frame the generated answer will be English. This is scoped to the answer card and does not introduce application-wide locale state.

### 5. Cover the production-shaped failure in tests and evals

Regression tests will use a gateway that deliberately returns Chinese for an English prompt on the first attempt and English on repair, plus a gateway that remains Chinese and must fail closed. Fixtures will include a Chinese session title, Chinese question, and Chinese material evidence. Chinese-session tests remain unchanged. AI eval cases will assert English output for mixed-source-language inputs without storing real user content.

## Risks / Trade-offs

- [A valid English technical answer contains Chinese code strings or a company name] → Use a materiality threshold rather than rejecting every Han character, and test short proper nouns inside a long English answer.
- [Buffering delays the first visible token] → Reuse the existing quick normalization buffer and keep the detail guard prefix small; record the retry count without content.
- [The model repeatedly ignores the language contract] → Fail closed with a stable retryable user action instead of displaying a misleading successful answer.
- [A Chinese regression is introduced by shared code] → Activate prompt blocks, validation, repair, and labels only when the authoritative session language is `en-US`.

## Migration Plan

Deploy prompt assets and backward-compatible backend/Web code together. Run synthetic Chinese-evidence English-session smoke tests before production. No database or desktop migration is required. Rollback restores the previous Backend/Web image; stored session language values remain valid and the Chinese path is unchanged.

## Open Questions

None for this defect scope. The initial guard allows small proper-noun exceptions; future multilingual code-answer requirements can tune the threshold from eval evidence.
