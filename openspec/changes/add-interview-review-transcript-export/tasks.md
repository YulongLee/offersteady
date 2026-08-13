## 1. Backend review snapshot

- [x] 1.1 Add typed review transcript and session snapshot response schemas.
- [x] 1.2 Add an owner-authorized ended-session review endpoint backed by persistent final realtime context entries.
- [x] 1.3 Add backend regressions for role mapping, chronological order, interim exclusion, cross-account denial, and deleted-session denial.

## 2. Web review and export

- [x] 2.1 Extend the Web domain and backend adapter to load the current session review snapshot together with existing answer history.
- [x] 2.2 Add a pure Markdown review formatter with safe filename generation and a browser-local download helper.
- [x] 2.3 Update the review page to show real interviewer/candidate transcript separately from AI answer advice, including loading and empty states.
- [x] 2.4 Add the explicit local download action and privacy notice without uploading a generated attachment.

## 3. Verification

- [x] 3.1 Add focused Web tests for transcript rendering, semantic separation, Markdown content, download behavior, and mobile layout.
- [x] 3.2 Run focused and full Backend/Web tests, Web typecheck/build, JSON/Markdown checks, and strict OpenSpec validation.
- [x] 3.3 Review the diff for privacy, ownership isolation, API compatibility, and unrelated changes.
