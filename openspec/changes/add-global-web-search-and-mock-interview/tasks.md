## 1. Global entitlement foundation

- [x] 1.1 Implement immutable seven-day plan eligibility and regression tests (near expiry, Free/day pass, revoked/future/expired).
- [x] 1.2 Implement Global-only mock migration, atomic three-per-UTC-day quota/two-record limit, no-wallet metering and fault compensation; verify isolated PostgreSQL concurrency and CN regression.

## 2. Global mock interview

- [x] 2.1 Wire default-off Global runtime, English prompts/TTS/ASR, English errors and provider-contract/evaluation tests without changing companion behavior.
- [x] 2.2 Add English sidebar, preparation, workbench, playback, saved reports and Word export with eligibility/quota copy; test lifecycle and export.

## 3. Global web detailed answer

- [x] 3.1 Wire opt-in detailed-only provider flow through Global membership authorization; retain ordinary quick answer, cancellation and fallback behavior.
- [x] 3.2 Add toolbar toggle/status/sources/eligibility copy and regression tests for slow search, toggling off and late events.

## 4. Verification and rollout

- [x] 4.1 Run backend, CN regression, Global frontend/build and synthetic evaluation suites; validate OpenSpec and record exact outcomes.
- [x] 4.2 Produce an isolated candidate from the live Global baseline and verify Global provider permissions with synthetic inputs.
- [ ] 4.3 Verify a real companion practice round, English audio/report/Word and ordinary interview regression (user requested deployment on 2026-09-29; real-device acceptance deferred to the post-release user test, not marked passed).
- [x] 4.4 Confirm an idle deployment window, retain baseline/configuration rollback, deploy only Global and verify payment/language/normal interview/new feature health.

验证记录：`docs/releases/global-practice-local-20260929.md`、`docs/releases/global-practice-production-20260929.1.md`。发布前重新运行候选后台 142 项、前端 158 项通过，无跳过；国际服既有凭证的合成 TTS/ASR、联网、英文出题/报告实际调用通过。2026-09-29 已仅发布国际服 Backend/Web，鉴权、连接、支付配置、语言、安装包及线上健康检查通过。真实助手联调和完整普通面试人工体验仍未完成，保留 4.3。
