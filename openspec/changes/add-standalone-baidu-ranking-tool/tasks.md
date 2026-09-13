## 1. Tool structure and configuration

- [x] 1.1 Add an isolated local tool package and command entry point outside production app startup paths.
- [x] 1.2 Add server/provider endpoint, credential, domain, keyword, timeout, retry, and output configuration with secret redaction.
- [x] 1.3 Add setup documentation showing local env-file usage and credential rotation guidance.

## 2. Ranking client and reports

- [x] 2.1 Implement the Baidu PC ranking adapter with form encoding, supported authentication modes, bounded timeout, and retry.
- [x] 2.2 Parse and validate up to 50 results, distinguishing ranked, not-found, authentication, quota, timeout, and provider errors.
- [x] 2.3 Implement single-keyword and explicit batch commands with request-rate limits.
- [x] 2.4 Implement JSON and Markdown export with credential and authorization-header redaction.

## 3. Verification

- [x] 3.1 Add unit tests for configuration secrecy, authentication selection, response parsing, rank semantics, retry, and error mapping.
- [x] 3.2 Add CLI tests proving missing credentials cause no provider request and batch mode is bounded.
- [x] 3.3 Run Python syntax checks, unit tests, and `openspec validate add-standalone-baidu-ranking-tool --strict` (repository ruff/mypy are not installed).

## 4. Handoff

- [x] 4.1 Run one controlled query with user-supplied credentials only after local configuration is confirmed.
- [x] 4.2 Provide the generated report and usage instructions for continuing analysis in the current conversation.
- [x] 4.3 Confirm no production deployment or admin-platform change was performed.
