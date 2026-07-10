## 1. Backend runtime readiness

- [x] 1.1 Audit the live-answer runtime path from Settings injection through `ChatService` and `QwenCompatibleGateway` to confirm `.env` model config is actually used in non-test execution.
- [x] 1.2 Fix any runtime branch that incorrectly falls back to placeholder or synthetic behavior when `.env` chat configuration is present.
- [x] 1.3 Add structured error classification for missing config, auth failure, provider unavailability, rate limiting, and invalid provider responses in the live-answer backend path.
- [x] 1.4 Ensure backend logs and responses expose only safe diagnostics without leaking API keys, prompts, or sensitive user content.

## 2. Live interview frontend behavior

- [x] 2.1 Audit the live interview manual-answer / quick-answer frontend path to ensure it always calls backend live-answer APIs instead of local success fallbacks.
- [x] 2.2 Update frontend error mapping so the interview page shows backend-provided safe model-readiness errors while preserving the original question for retry.
- [x] 2.3 Keep the current interview page layout unchanged while aligning answer pending / failed / retry states with the real backend runtime.

## 3. Verification and documentation

- [x] 3.1 Add backend regression coverage for `.env`-configured model success and for each major model-unavailable failure class.
- [x] 3.2 Add frontend regression coverage for quick-answer failure feedback and retry behavior when the backend reports model runtime issues.
- [x] 3.3 Update prompt-linked evals and local runtime documentation if needed so live-answer readiness can be verified consistently in development.
- [x] 3.4 Run `openspec validate fix-live-interview-model-runtime-from-env --strict`.
