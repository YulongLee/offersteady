## 1. Scope and acceptance

- [x] 1.1 Inspect existing session, billing, resume, desktop capture boundaries and official Qwen realtime TTS protocol
- [x] 1.2 Confirm three daily free creations for active time members, full 100-point-plus-5-per-minute pricing thereafter, manual answer completion and two saved records per owner
- [x] 1.3 Confirm transcript/report retention policy and obtain approval of the complete feature design before application implementation
- [x] 1.4 Resolve cancellation and irrecoverable-provider-failure refund policy before enabling paid creation for real users
- [x] 1.5 Approve the business-day reset timezone, session entitlement locking, rounding, pause, expiry and fault-wait billing semantics

## 2. Backend lifecycle and creation billing

- [x] 2.1 Add mock session schemas, owner isolation, state/version constraints and additive persistence migration
- [x] 2.2 Add atomic/idempotent 100-point paid creation and three-slot daily member entitlement with concurrent, failed-creation and last-free-slot price-change regression tests
- [x] 2.3 Require usable owner-selected resume version and authorized desktop binding before start; reject bypass via old lifecycle endpoints
- [x] 2.4 Implement idempotent 5-point minute metering with approved member exemptions; prevent duplicate ordinary-minute and per-answer charges and exclude ordinary quick-answer/screenshot actions
- [x] 2.5 Add bounded round submission, refresh recovery, ten-question enforcement and early-end report transitions
- [x] 2.6 Enforce two saved records per owner atomically, including concurrent saves, idempotent repeats and owner-authorized deletion that preserves the ledger
- [x] 2.7 Persist session billing class and quota date independently of saved history; test paid fourth-session minute fees, daily reset and cross-day creation retries

## 3. Interview generation and feedback

- [x] 3.1 Add centralized question/report/TTS prompts and typed provider outputs with evidence and injection boundaries
- [x] 3.2 Read the selected parsed resume version with explicit context limits instead of relying only on short summaries
- [x] 3.3 Implement contextual next-question generation, failure recovery and server-side single advancement
- [x] 3.4 Implement scored reports, per-question suggestions, insufficient-evidence states and approved retention/deletion behavior
- [x] 3.5 Add synthetic evals for different resume roles, follow-ups, empty answers, injection, invented experience, repeated questions and partial reports

## 4. Speech and resource lifecycle

- [x] 4.1 Add server-only Qwen realtime TTS configuration and replaceable adapter with bounded buffers, deadlines and cancellation
- [x] 4.2 Add authenticated browser playback with speaking/listening states and explicit text fallback on speech failure
- [x] 4.3 Implement microphone-only input and authoritative per-round capture gating; reject playback echo and stale transcripts
- [x] 4.4 Verify existing desktop compatibility or document and implement the minimum required companion capability without publishing it
- [x] 4.5 Close ASR/TTS/tasks and clear transient state on completion, early end, expiry, disconnect cleanup and shutdown

## 5. Web experience

- [x] 5.8 Rename the CN feature to 模拟面试 across navigation, new default titles and notices; retain AI identity disclosure and verify locally without deployment

- [x] 5.1 Add the CN sidebar entry under written-exam mode and isolated mock routes with default-off feature capability
- [x] 5.2 Show remaining daily free quota, this session's price, 100-point paid creation and 5-point minute pricing; confirm paid creation after quota exhaustion and support preparation with resume/machine-code selection
- [x] 5.3 Generate an original AI interviewer visual using the imagegen skill and integrate accessible speaking/listening state styling
- [x] 5.4 Implement current question, progress, editable transcript confirmation, manual answer completion and end controls
- [x] 5.5 Implement report scoring, per-question feedback, saved count (0/2, 1/2, 2/2), full-quota messaging and approved automatic save/delete behavior
- [x] 5.6 Add an actual-playback-driven waveform below the interviewer portrait with idle cleanup, static reduced-motion status and no changes to billing or microphone routing
- [x] 5.7 Verify waveform level changes, silence, pause/end/disconnect cleanup and desktop/mobile local synthetic playback; record tests without deploying
- [x] 5.9 Add completed-report Word download with local generation, truthful scoring/partial states, full question-answer feedback, safe filenames, lazy loading and retry; no billing or companion changes
- [x] 5.10 Test report export content, long text, empty scores, download interaction and existing exports; render a synthetic DOCX and inspect all pages, then record local checks without deployment

## 5A. Existing companion compatibility (implemented locally; CN release authorized)

- [x] 5A.1 Add an isolated backend adapter for the shipped v2 microphone publisher; remove the mandatory new companion capability
- [x] 5A.2 Separate preparation readiness from actual audio connection; show truthful capture/privacy and waiting states without charging for connection waits
- [x] 5A.3 Verify legacy framing, round fences, duplicates, reconnect, ownership, bounded cleanup and ordinary interview isolation locally; do not deploy or publish an assistant

## 6. Local verification and handoff

- [x] 6B.1 Following the user's 2026-09-26 deployment approval, release only the feature rename and completed-report Word download to CN on the verified readiness-2 production baseline; rerun scoped regressions, check no active ordinary/mock interviews immediately before switching, retain rollback images and verify public health, assets and unchanged configuration/services. Do not update the companion, global deployment, billing rules or historical records.

- [x] 6A.1 Fix shipped v2 companion unknown permission readiness without treating explicit denial as permission; expose actionable preparation status and preserve same-session billing
- [x] 6A.2 Reproduce the shipped heartbeat capabilities in regression tests, verify unknown/denied/offline/binding failures and existing audio/ordinary paths, then deploy CN only during an idle window

- [x] 6.1 Run backend lifecycle/authorization/creation-and-minute-billing tests and real local PostgreSQL concurrency/migration tests with synthetic accounts, including the two-record cap
- [x] 6.2 Run web component tests, type checking, build and desktop/mobile viewport inspection
- [x] 6.3 Run ordinary interview, mobile audio, written-exam, quick-answer and billing regression tests
- [x] 6.4 Verify the configured real Qwen TTS using synthetic text; record first-audio latency and closure without saving keys or user audio
- [ ] 6.5 Verify real microphone and desktop binding locally, including speaker echo, headphones, refresh, reconnect and termination during playback
- [x] 6.6 Run repeated synthetic sessions and failure injection; verify bounded memory/resources and no duplicate debit or question advancement
- [x] 6.7 Run AI evals, strict OpenSpec validation and Markdown link checks; record only executed results and remaining acceptance gaps
- [x] 6.8 Following the user's 2026-09-26 instruction to deploy first and test afterward, deploy only CN on its verified production baseline after automated/provider checks and during a no-active-interview window; verify health and rollback readiness. Keep 6.5 explicitly pending for the user's post-release real-device acceptance. Do not publish a new assistant or push Git without separate authorization.
