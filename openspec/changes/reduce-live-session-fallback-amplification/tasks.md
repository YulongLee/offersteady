## 1. Backend Recovery Snapshot

- [x] 1.1 Add an authorized aggregated live-session snapshot response and service method that reuse existing runtime, transcript, candidate, and event sources
- [x] 1.2 Add the snapshot route without changing the existing individual endpoint contracts
- [x] 1.3 Add backend tests for ownership, active page lease, complete snapshot shape, cursor continuity, terminal sessions, and old endpoint compatibility

## 2. Web Stream Lifecycle

- [x] 2.1 Refactor the live-session subscription into one cancellable lifecycle that becomes healthy only after the first authoritative snapshot
- [x] 2.2 Replace one-second four-endpoint refresh with one aggregated hydration/recovery request and immediate then 2/4/8/15-second non-overlapping reconnect backoff
- [x] 2.3 Cancel every reconnect and fallback timer on stream recovery, page inactivity, session termination, navigation, or unmount while preserving current visible state
- [x] 2.4 Add web regressions for healthy-stream zero polling, disconnection recovery, stale callback suppression, terminal cleanup, and unchanged quick/screenshot/stop-answer behavior

## 3. Same-Browser Coordination

- [x] 3.1 Add a BroadcastChannel-based leader lease for the same interview session with safe fallback when the API is unavailable
- [x] 3.2 Relay authoritative snapshots and incremental events from leader to followers with page instance and epoch guards
- [x] 3.3 Add tests for duplicate tabs, leader close/takeover, stale leader events, and no restriction across independent browser contexts

## 4. Delivery Observability

- [x] 4.1 Record content-free Web delivery timing and reconnect/fallback counters using existing telemetry boundaries
- [x] 4.2 Classify backend request samples as control API, recovery snapshot, or SSE handshake while retaining aggregate API P95 compatibility
- [x] 4.3 Add metrics tests proving request classification and absence of user content fields

## 5. Verification And Release

- [x] 5.1 Run focused backend and web tests after each implementation area and validate the OpenSpec change strictly
- [x] 5.2 Run full backend/web regressions, typecheck, production build, and synthetic 1/5/10-session plus disconnect load tests
- [x] 5.3 Document before/after request rate, P95/P99, CPU, reconnect, fallback, errors, compatibility, rollout, and rollback results
- [x] 5.4 Commit and push scoped changes, deploy Backend before Web with health gates, verify production endpoints and logs, and retain the prior images for immediate rollback
