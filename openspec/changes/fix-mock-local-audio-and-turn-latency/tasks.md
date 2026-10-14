## 1. Approved scope

- [x] 1.1 Record the confirmed diagnosis, user authorization, local-only scope and acceptance scenarios.

## 2. Mac audio

- [x] 2.1 Add audio-input entitlements to main/helper signing and verify actual bundle entitlements.
- [x] 2.2 Preserve actionable microphone failures and consistent mock device capabilities; add regression tests.

## 3. Mock turn lifecycle

- [x] 3.1 Fence old audio and detach bounded cleanup before publishing/starting next generation; test blocked-close and stale-audio races.
- [x] 3.2 Make disconnected microphone cleanup idempotent and verify ordinary/mock isolation.

## 4. Generation diagnostics

- [x] 4.1 Add safe stage timings and error classification while preserving retries, provider-fault counts, prompts and model configuration.
- [x] 4.2 Run failure-injection and privacy regressions, including malformed and repeated output.

## 5. Local verification and handoff

- [x] 5.1 Run scoped Backend/Desktop/Web checks and strict OpenSpec/link validation; record executed results and limits.
- [x] 5.2 Compile a clearly identified local Mac test artifact, inspect actual signatures/version and make the relevant local test flow available.
- [x] 5.3 Record local usage and user physical-microphone acceptance steps; do not deploy or publish online.
- [x] 5.4 Compile and verify a second CN-connected client test artifact on the same tested code, following the user's online-connection clarification; preserve existing installed app and do not update online services.

Executed results and remaining user physical-microphone acceptance: [local handoff](../../../docs/releases/mock-local-audio-and-turn-latency-20261015.1.md).
