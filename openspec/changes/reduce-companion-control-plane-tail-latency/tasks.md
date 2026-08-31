## 1. Desktop control-plane load

- [x] 1.1 Add regression tests for adaptive waiting/live binding intervals and non-overlapping scheduling
- [x] 1.2 Implement server-suggested waiting interval with a 1-second floor while preserving the 2-second live lease interval
- [x] 1.3 Add regression tests for device-status semantic deduplication, immediate transitions, keepalive and retry
- [x] 1.4 Implement change-driven device-status reporting with a 15-second keepalive

## 2. Screenshot stream lifecycle

- [x] 2.1 Add tests proving capture runtime state changes do not restart an eligible screenshot SSE
- [x] 2.2 Restrict screenshot SSE start/stop to connection-eligibility boundary changes and preserve one owner

## 3. Runtime metrics

- [x] 3.1 Add backend tests that classify realtime and screenshot stream routes independently from ordinary API latency
- [x] 3.2 Exclude SSE connection duration from ordinary API P95/P99 while retaining separate stream counts and duration metrics

## 4. Verification and release

- [x] 4.1 Run focused desktop/backend tests and relevant typecheck/build suites
- [x] 4.2 Validate the OpenSpec change strictly and document executed verification
- [x] 4.3 Confirm production activity, deploy with rollback readiness, and run health/core endpoint smoke tests
- [x] 4.4 Compare production request rates, ordinary API P95 and errors after deployment without recording user content
