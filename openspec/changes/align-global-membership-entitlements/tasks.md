## 1. Global commerce model and persistence

- [x] 1.1 Extend GlobalPlan and GlobalEntitlement with versioned knowledge Token allowances and used/locked counters.
- [x] 1.2 Add a forward-compatible PostgreSQL migration for knowledge quota columns and update repository reads/writes/reservations.
- [x] 1.3 Publish the recommended Global catalogue values: 1-day 0, 7-day 50,000, 30-day 200,000, and 90-day 1,000,000 knowledge Tokens.

## 2. Global usage and API behavior

- [x] 2.1 Enforce tiered knowledge quotas through quote, reserve, settle, release, idempotency, and ownership checks.
- [x] 2.2 Expose active entitlement remaining time, subscription renewal/cancellation status, and knowledge usage in Global Commerce state and catalogue payloads.
- [x] 2.3 Preserve paid realtime/screenshot entitlement billing and ensure no domestic points ledger is touched on the global edition.

## 3. International web billing experience

- [x] 3.1 Add a Global billing adapter that consumes `/api/v1/global-commerce/*` and maps plans, subscription state, time remaining, and usage into the UI model.
- [x] 3.2 Render a Global-only membership page without domestic points, ledger, redemption, or domestic payment controls.
- [x] 3.3 Show server-authoritative remaining time, renewal state, screenshot inclusion, realtime inclusion, and knowledge Token used/remaining values.

## 4. Verification and delivery

- [x] 4.1 Add backend regression tests for all plan tiers, quota exhaustion, failed upload release, screenshot non-point billing, and historical snapshots.
- [x] 4.2 Add web regression tests for Global state rendering and ensure Chinese billing tests remain unchanged.
- [x] 4.3 Run targeted tests, typecheck, build, strict OpenSpec validation, and relevant existing tests.
- [ ] 4.4 Deploy only the verified revision to the international server and verify catalogue, state, checkout, screenshot, and knowledge quota flows without changing domestic production.
