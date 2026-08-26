## 1. Session Contract And Persistence

- [x] 1.1 Add the closed `zh-CN | en-US` interview-language domain type and expose `interviewLanguage` in backend session schemas and Web domain models, with `zh-CN` as the compatibility default.
- [x] 1.2 Add a forward-only database migration for a non-null `interview_language` session column, backfill existing rows to `zh-CN`, and update production/in-memory repositories with persistence round-trip tests.
- [x] 1.3 Add an owner-authorized preparation-state language update command/API, reject invalid values and live/ended mutations, and cover concurrent start/update behavior with service and route tests.
- [x] 1.4 Make session restart inherit the original language while remaining editable before the restarted session begins, and add regression tests for old-client creation and restart behavior.

## 2. Preparation Experience

- [x] 2.1 Add an accessible preparation-page selector for “中文面试” and “English Interview”, explain that it controls recognition and answer language, and keep the existing readiness calculation unchanged.
- [x] 2.2 Wire selection changes to the authoritative session API, restore the persisted value after refresh/re-entry, roll back failed optimistic changes, and render the value read-only after start.
- [x] 2.3 Add Web tests for the default Chinese path, persisted English path, save failure, refresh recovery, and unchanged material/device start requirements.

## 3. Realtime Speech And Question Routing

- [x] 3.1 Resolve the authoritative language before realtime ASR prewarm/ingestion and carry it through per-session/per-source runtime state without accepting a publisher override.
- [x] 3.2 Map `zh-CN` and `en-US` to provider-specific realtime ASR session-update language values, keep connection/cache identity language-safe, and preserve language across reconnects and source rebuilds.
- [x] 3.3 Make question detection and normalization language-aware for English interrogatives, incomplete statements and punctuation while preserving dual-channel interviewer-only automatic triggering.
- [x] 3.4 Add ASR payload, English partial/final delivery, reconnect, cross-language isolation, English question triggering and Chinese regression tests using synthetic audio/transcript fixtures.

## 4. English Prompt And Answer Pipeline

- [x] 4.1 Add versioned English `system`, `quick`, `detail` and `continuation` prompt assets under `ai/prompts/chat-service/`, preserving the current Chinese files and grounding/no-fabrication policy.
- [x] 4.2 Implement a language-aware chat prompt resolver and localize prompt-builder constants and streamed stage labels so ordinary, quick, detailed and continuation answers remain consistently English in `en-US` sessions.
- [x] 4.3 Add a versioned English screenshot-answer prompt and language-aware screenshot prompt construction, including English fallback instruction and evidence/fact/inference separation.
- [x] 4.4 Make a missing English prompt asset fail closed with a recoverable error, and add unit/integration tests proving it never falls back to a Chinese template.
- [x] 4.5 Add service integration tests for automatic and manual English questions, English answers grounded in Chinese/English materials, streaming stage continuity, screenshot answers, and unchanged Chinese outputs.

## 5. Evaluation, Observability And Security

- [x] 5.1 Add synthetic or de-identified `ai/evals/` cases for English question normalization, interviewer-first triggering, quick/detail/continuation quality, mixed-source-language grounding and screenshot answering.
- [x] 5.2 Extend structured telemetry with the normalized language, stage and prompt template ID/version while retaining hash/length-only content logging, and add log-redaction tests for transcript, screenshot and personal-material content.
- [x] 5.3 Run the new English eval suite together with existing Chinese baselines, document thresholds and resolve any regression before release.

## 6. Release And Production Verification

- [x] 6.1 Run backend tests, Web tests/build, AI evals, migration checks and `openspec validate add-interview-language-routing --strict`; record exact results without using real user content.
- [x] 6.2 Deploy the additive migration and backward-compatible backend first, verify English prompt assets and DashScope English realtime session-update connectivity without printing API keys, then deploy the Web selector.
- [x] 6.3 Perform controlled production Chinese and English dual-channel interviews covering refresh/re-entry, ASR reconnect, automatic question detection, streaming quick/detail/continuation and screenshot answers; compare latency/error metrics and keep English gated if thresholds fail.
- [x] 6.4 Confirm the desktop audio protocol is unchanged and do not increment the companion version; if implementation reveals a required desktop modification, stop and obtain approval for a separately versioned desktop release.
