## 1. Backend lease ownership

- [x] 1.1 Add page instance, generation, and expiry to Web heartbeat records
- [x] 1.2 Implement atomic user-level live page claim in memory and Redis repositories
- [x] 1.3 Validate live page lease before and during SSE streaming

## 2. Web page lifecycle

- [x] 2.1 Carry page lease identity through heartbeat and realtime stream requests
- [x] 2.2 Coordinate same-browser takeover with BroadcastChannel
- [x] 2.3 Pause replaced pages, abort work, and disable interactive controls

## 3. Regression coverage

- [x] 3.1 Add backend regression coverage for lease takeover and stale stream rejection
- [x] 3.2 Add frontend adapter coverage for lease request propagation
- [x] 3.3 Run backend and frontend test suites
- [x] 3.4 Run strict OpenSpec validation
