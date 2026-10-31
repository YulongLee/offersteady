## 1. Scope and baseline

- [x] 1.1 Read current baseline, diagnosis and mock/device/billing specifications; record the user's mock-only, no-companion and local-only authorization.
- [x] 1.2 Define testable permission, bounded waiting, recovery and playback lifecycle scenarios; reach apply-ready and strict validation.

## 2. Backend readiness

- [x] 2.1 Distinguish dedicated unknown/checking from explicit denied without rewriting permission or weakening identity/lifecycle/legacy rules.
- [x] 2.2 Add regression coverage for publish/start recovery, granted transitions and rejection before generation/capture with unchanged deadline/billing.

## 3. Mock webpage recovery

- [x] 3.1 Add bounded checking guidance, throttled same-session recheck through existing heartbeat and stale readiness-error cleanup; test lifecycle cleanup without new polling.
- [x] 3.2 Add separate bounded browser playback recovery with connection/question/operation fencing and repeat-command protection; add race and failure regressions.

## 4. Local acceptance

- [x] 4.1 Run relevant Backend and complete CN Web regressions, typecheck/build and synthetic browser smoke; preserve unrelated local modifications.
- [x] 4.2 Independently review scope and failure boundaries, validate OpenSpec and documentation links, and record test results and physical-device limitations without deployment/Git.

Executed results, historical failures and physical-device limits: [local handoff](../../../docs/releases/cn-mock-permission-local-20261030.1.md).

## 5. Requested copy simplification

- [x] 5.1 Move long preparation instructions below start in a collapsed disclosure, shorten repeated notices and fold local-only QA controls/receipt; preserve all functional behavior and do not deploy.
- [x] 5.2 Run existing mock UI/player tests, typecheck and OpenSpec validation; verify the local compact view and update the handoff.

## 6. Follow-up local review

- [x] 6.1 Reproduce queued-playback interruption, late resume response and post-end settling timer using actual components and synthetic services; distinguish existing backend issues from new regressions.
- [x] 6.2 Fence late selection/binding results and cancel pending microphone timers on control intents; add regression cases.
- [x] 6.3 Recover from interrupted queued playback without stale context callbacks or automatic microphone restart; add regression cases.
- [x] 6.4 Run final local regressions, typecheck/build, strict validation and scope review; document remaining actual backend issues without changing their behavior or deploying.
