## 1. Protocol and Session Contract

- [x] 1.1 Audit current desktop `sourceKind` / transcript role mapping and remove any remaining cross-session fallback paths.
- [x] 1.2 Update shared protocol/runtime types so companion, backend and web all describe current-session realtime sync with the same diagnostics vocabulary.
- [x] 1.3 Add regression coverage for session-scoped filtering and dual-role transcript expectations.

## 2. Backend Realtime Routing

- [x] 2.1 Ensure Realtime Speech writes `microphone` frames as current-session “我” transcripts and `system` frames as current-session “面试官” transcripts.
- [x] 2.2 Ensure transcript, candidate and runtime APIs return only the active session data requested by the web live page.
- [x] 2.3 Add stage-specific diagnostics for capture-missing, upload-missing, ASR-failed, web-not-consuming and stale-binding cases.
- [x] 2.4 Add backend tests covering current-session transcript routing, cross-session filtering and diagnostic stage reporting.

## 3. Desktop Companion Bridge

- [x] 3.1 Keep local monitor feedback alive until the realtime publisher has actually taken over the corresponding source.
- [x] 3.2 Ensure companion publisher emits current-session frames for both microphone and system audio using the bound machine/session context.
- [x] 3.3 Surface per-stage companion diagnostics that distinguish local capture failure from websocket/backend failure.
- [x] 3.4 Add desktop tests for publisher takeover, local-monitor fallback and dual-source health display.

## 4. Web Live Conversation Consumption

- [x] 4.1 Update the live interview page to render current-session realtime transcripts as “面试官 / 我” in the existing realtime conversation panel.
- [x] 4.2 Ensure the live page empty/error states reflect current-session diagnostics instead of historical placeholder text.
- [x] 4.3 Ensure quick answer only reads the latest current-session interviewer transcript, not stale or cross-session content.
- [x] 4.4 Add web tests covering realtime transcript rendering, empty-state diagnostics and quick-answer session scoping.

## 5. End-to-End Verification

- [x] 5.1 Verify locally that binding a companion to a live interview produces visible “我 / 面试官” realtime transcripts on the web page.
- [ ] 5.2 Verify that closing the live page or switching sessions stops realtime conversation updates for the previous session.
- [x] 5.3 Update runtime/integration diagnostics docs with the realtime conversation troubleshooting flow.
- [x] 5.4 Add or update AI evals if quick-answer grounding behavior changes with current-session interviewer transcript selection.
