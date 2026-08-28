## 1. Visible-page subscription ownership

- [x] 1.1 Extend the browser leader coordinator with explicit eligible/ineligible transitions and immediate release takeover
- [x] 1.2 Connect document visibility to leader eligibility and cancel hidden-page realtime streams without affecting desktop capture
- [x] 1.3 Add deterministic tests for hidden leader release, visible takeover, two visible pages and timer cleanup

## 2. Bounded first-snapshot recovery

- [x] 2.1 Add a two-second first authoritative snapshot deadline to the SSE consumer with complete reader/timer cleanup
- [x] 2.2 Classify first-snapshot timeout separately and record content-free delivery recovery metrics
- [x] 2.3 Apply one aggregate recovery snapshot and immediately rebuild SSE after successful recovery while retaining bounded backoff on failure
- [x] 2.4 Add adapter and App regression tests for timeout, successful snapshot, immediate recovery, non-overlap and healthy push-only behavior

## 3. Verification and release

- [x] 3.1 Run focused Web tests, full Web tests, TypeScript typecheck and the production Web build
- [x] 3.2 Validate this OpenSpec change strictly and document the implementation and rollback behavior
- [x] 3.3 Deploy the minimum required production services, pass health/version/error-rate gates and preserve rollback artifacts
- [ ] 3.4 Run a privacy-safe production acceptance test for first-transcript delivery and hand the live page back to the user for confirmation

## 4. First-visible regression hardening

- [x] 4.1 Preserve one healthy SSE when the sole live page becomes hidden and transfer immediately when a visible follower probes
- [x] 4.2 Consolidate Backend first-snapshot hydration and prevent runtime diagnostic failures from terminating transcript delivery
- [x] 4.3 Add a dedicated Nginx SSE route without WebSocket upgrade, buffering, caching or compression
- [x] 4.4 Add coordinator, Web adapter, Backend stream and proxy regressions for the observed eight-second failure mode
- [x] 4.5 Run focused/full Web and Backend tests, type checks, production builds and strict OpenSpec validation
- [ ] 4.6 Start the local companion and run a privacy-safe first-visible physical acceptance test with the user
