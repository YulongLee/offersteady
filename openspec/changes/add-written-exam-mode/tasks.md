## 1. Session contract and persistence

- [x] 1.1 Add the shared `interview | written` session-mode contract with `interview` compatibility defaults.
- [x] 1.2 Add an additive PostgreSQL migration and repository mappings for session mode and verify existing rows remain interviews.
- [x] 1.3 Extend create, list, detail, continuation and desktop-binding payloads with the authoritative session mode.
- [x] 1.4 Auto-confirm an empty material binding for written sessions while preserving normal interview material behavior.

## 2. Written exam billing

- [x] 2.1 Add `written_exam_entry` to billing contracts and expose the server-owned `writtenExamPoints` rate fixed at 30.
- [x] 2.2 Implement wallet-only idempotent reserve, settle and release behavior for the written-exam entry usage.
- [x] 2.3 Orchestrate written-session start so insufficient balance blocks activation, success charges once and failures release the reservation.
- [x] 2.4 Add billing ledger descriptions, API serialization and UI disclosure for the 30-point entry plus normal screenshot fees.

## 3. Backend mode isolation

- [x] 3.1 Add a reusable backend guard that rejects speech publisher, audio control and frame operations for written sessions.
- [x] 3.2 Reject quick, manual and auto-answer commands for written sessions without creating tasks or charges.
- [x] 3.3 Keep screenshot capture, upload, vision streaming, history and ending available for active written sessions.
- [x] 3.4 Preserve the existing single-active-session, continuation and end-session rules across both modes.

## 4. Web experience

- [x] 4.1 Add initial mode-aware session creation and clear 笔试模式 pricing/capability copy.
- [x] 4.2 Render a lightweight written preparation page whose only readiness gate is companion binding plus conflict resolution.
- [x] 4.3 Render a screenshot-only written workspace without transcript, quick/manual/auto-answer or audio controls/effects.
- [x] 4.4 Make home, continue, preparation, active and ended navigation labels mode-aware without changing existing interview layout.
- [x] 4.5 Replace the creation-level mode selector with separate 面试模式 and 笔试模式 sidebar destinations and creation routes.
- [x] 4.6 Restore the interview creation page to the pre-feature UI and isolate interview/written current and recent lists.
- [x] 4.7 Replace the written preparation two-column explainer with one compact companion setup surface and only the mandatory entry-fee disclosure.

## 5. Companion behavior

- [x] 5.1 Propagate session mode through the companion binding/control snapshot using a backward-compatible field.
- [x] 5.2 Keep heartbeat, screenshot push/fallback and upload active for written sessions while preventing media acquisition, publisher creation and ASR traffic.
- [x] 5.3 Add regression coverage proving written mode does not request or start microphone/system-audio capture.

## 6. Verification and release

- [x] 6.1 Add backend tests for migration defaults, empty materials, 30-point success, insufficient balance, retry idempotency and release on failure.
- [x] 6.2 Add backend integration tests proving written mode rejects speech/chat operations and accepts screenshot operations.
- [x] 6.3 Add Web tests for mode selection, lightweight preparation, screenshot-only workspace, continuation and unchanged interview flow.
- [x] 6.4 Run focused and full backend/Web/companion tests, type checks, builds and strict OpenSpec validation using synthetic data only.
- [x] 6.5 Commit and push the isolated change, deploy the additive migration and compatible services, and verify health, charge idempotency, screenshot flow and zero written-mode audio/ASR activity.
- [x] 6.6 Confirm the recorded Git tag and retained production images can restore the pre-feature baseline.
- [x] 6.7 Add regression tests for separate navigation, route-owned creation mode and unchanged interview creation behavior.
- [x] 6.8 Run Web tests/build and strict OpenSpec validation, then deploy only the corrected Web service and verify both entry routes.
- [x] 6.9 Repair PostgreSQL billing constraints for `written_exam_entry` and add a migration contract regression test.
- [ ] 6.10 Run focused/full verification, deploy the minimal affected services and verify a real written session can enter exactly once.
