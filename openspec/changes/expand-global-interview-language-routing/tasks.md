## 1. Locale registry and persistence

- [ ] 1.1 Add the versioned multilingual locale registry, provider language codes, release tiers, RTL metadata, and shared protocol/domain types.
- [ ] 1.2 Add the user default interview-language setting with authenticated read/write API, validation, migration, and persistence round-trip tests.
- [ ] 1.3 Extend session creation/update schemas and repositories to persist the selected locale, preserve legacy defaults, and lock it after start.
- [ ] 1.4 Add capability gating so only locales with provider access, prompt assets, and passing release checks can start production sessions.

## 2. Global Web experience

- [ ] 2.1 Add default interview-language controls to the existing Settings page without changing the current layout or visual tokens.
- [ ] 2.2 Replace the Global preparation page's fixed English control with the registry-backed selector, Production/Beta labels, persistence, refresh recovery, and save-error rollback.
- [ ] 2.3 Render the locked locale in live, review, written-exam, and export surfaces using the existing badge and typography patterns.
- [ ] 2.4 Add localized UI copy for selector descriptions, capability warnings, RTL direction, and recoverable errors while preserving existing English commercial copy.

## 3. Backend routing

- [ ] 3.1 Route realtime ASR prewarm, ingestion, reconnect, and source-session cache identity through the authoritative locale registry.
- [ ] 3.2 Route question detection/normalization, chat quick/detail/continuation, screenshot analysis, fallback, review, and export formatting through the session locale.
- [ ] 3.3 Reject request-level language overrides and return stable errors for unsupported, unavailable, or mismatched locales.
- [ ] 3.4 Add provider adapter contract tests for all production locales and representative beta locales using synthetic audio/transcript/screenshot fixtures.

## 4. Prompt and commercial answer quality

- [ ] 4.1 Add independently versioned system/quick/detail/continuation/screenshot prompt assets for the ten production locales.
- [ ] 4.2 Add the shared commercial interview answer contract to every locale prompt: concise spoken delivery, conclusion-first structure, evidence grounding, uncertainty labels, no fabricated experience, and AI-advice disclosure.
- [ ] 4.3 Add beta prompt scaffolding and fail-closed checks so incomplete locales cannot silently use Chinese or English templates.
- [ ] 4.4 Add locale-aware output validation and one bounded repair retry for materially wrong-language responses.

## 5. Evaluation, privacy, and observability

- [ ] 5.1 Add synthetic AI eval cases for production locales covering normalization, interviewer-first triggering, quick/detail/continuation, screenshots, code-language constraints, and Chinese-source grounding.
- [ ] 5.2 Add multilingual Web/Backend regression tests for settings, preparation, refresh, lock, reconnect, cross-language isolation, and unchanged Chinese/English behavior.
- [ ] 5.3 Extend telemetry with locale, tier, stage, template version, latency, token usage, and error category only; add redaction tests proving no user content is logged.
- [ ] 5.4 Run eval gates and document which locales qualify for Production versus Beta.

## 6. Verification and rollout

- [ ] 6.1 Run focused and full Web/Backend tests, typechecks, builds, migration checks, AI evals, and strict OpenSpec validation.
- [ ] 6.2 Verify DashScope ASR language codes, permissions, latency, and reconnect behavior in a non-production environment without exposing credentials.
- [ ] 6.3 Release settings and preparation selector behind a controlled Global flag; keep current English default until production locale gates pass.
- [ ] 6.4 Perform controlled smoke tests for at least Chinese, English, Japanese, French, and German, then promote additional locales only with evidence.
