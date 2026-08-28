## Why

Production English interviews can still receive Chinese answer bodies when the recognized question, session title, or personal materials are predominantly Chinese. The current English prompt selection is working, but its language instruction is not enforced strongly enough against real-provider language drift, and the existing tests only prove template routing rather than the language of provider output.

## What Changes

- Make English the non-negotiable output language for question normalization, quick answers, detailed answers, continuations, screenshot answers, and safe fallback content in `en-US` sessions, even when the question or evidence is Chinese.
- Add a server-side language guard that prevents a materially Chinese model response from being completed or shown as a successful English answer and supports a bounded English-only regeneration before failing safely.
- Keep `zh-CN` prompt selection and answer behavior unchanged.
- Localize answer-section labels that are part of the English live-answer surface without expanding into full application internationalization.
- Add real-provider-shaped regression fixtures and AI eval cases for Chinese questions and Chinese evidence inside English sessions.

## Capabilities

### New Capabilities

- `english-answer-language-enforcement`: Guarantees that every generated answer stage in an `en-US` interview remains English and fails safely instead of publishing a materially Chinese response.

### Modified Capabilities


## Impact

- Backend chat and screenshot prompt builders, provider-output validation, answer task failure/retry behavior, and content-free language telemetry.
- Versioned English prompt assets and synthetic AI evaluation cases.
- Web live-answer section labels and parsing for English answer headings.
- No database migration, desktop protocol change, audio persistence change, or new handling of real user content.
