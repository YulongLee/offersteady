## 1. Unified Event Foundation

- [x] 1.1 Add public session-event publishing and incremental cursor reads to the realtime repository/service boundary
- [x] 1.2 Change the session SSE endpoint to hydrate once and deliver ordered incremental events with resumable cursors
- [x] 1.3 Add backend tests for initial snapshot, cursor continuation, duplicate-safe identifiers, keepalive, and lease revocation

## 2. Remove Automatic Answer Internals

- [x] 2.1 Remove the unused answer executor, automatic-answer candidate state, execution methods, and legacy event publisher from RealtimeSpeechService
- [x] 2.2 Remove legacy automatic-answer adapter naming and prove that transcript/candidate confirmation never creates answer tasks
- [x] 2.3 Add or update AI evaluation cases and backend/web regressions for explicit-only answer triggering

## 3. Publish Answer And Screenshot Lifecycles

- [x] 3.1 Publish explicit live-answer task lifecycle updates into the unified session event stream
- [x] 3.2 Publish screenshot request create, claim, upload, completion, failure, and cancellation transitions without binary payloads
- [x] 3.3 Add backend lifecycle, ordering, safe-payload, and background-failure regression tests

## 4. Web Unified State Consumption

- [x] 4.1 Extend the web session event reducer to merge transcript, answer, and screenshot updates monotonically by identifiers and revisions
- [x] 4.2 Replace healthy-path screenshot status polling with session-event waiters and bounded exponential-backoff recovery
- [x] 4.3 Limit history refresh to hydration, explicit navigation, and stream recovery, then add duplicate/out-of-order/reconnect tests

## 5. Desktop Push-First Capture Delivery

- [x] 5.1 Add an authenticated desktop-device screenshot event SSE endpoint backed by the unified session event repository
- [x] 5.2 Update the desktop main process to keep one cancellable event subscription and process pushed request identifiers
- [x] 5.3 Retain the legacy next-request endpoint and enable one non-overlapping fallback poller only while push is unhealthy
- [x] 5.4 Add desktop tests for push delivery, duplicate suppression, reconnect, fallback activation, fallback cancellation, and shortcut direct processing

## 6. Verification And Release

- [x] 6.1 Run focused backend, web, desktop, AI eval, typecheck, and production build verification after each area
- [x] 6.2 Run the complete backend/web/desktop regression suite and validate this OpenSpec change strictly
- [x] 6.3 Update realtime runtime and desktop distribution documentation with the new event flow, metrics, compatibility, and rollback behavior
- [ ] 6.4 Commit scoped files, push Git, deploy Backend then Web, publish current desktop packages, and verify production health and event latency
