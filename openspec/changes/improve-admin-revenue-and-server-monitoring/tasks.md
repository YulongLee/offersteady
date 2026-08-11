## 1. Payment Diagnostics Persistence

- [x] 1.1 Add a backward-compatible migration for nullable signature, AppID, Seller ID, order and amount validation dimensions on payment callback events.
- [x] 1.2 Extend Alipay notification parsing to return independent cryptographic and merchant-identity results without persisting raw callback parameters.
- [x] 1.3 Persist safe validation dimensions and specific outcomes while retaining idempotent callback delivery handling.
- [x] 1.4 Add migration and repository regressions proving old callback rows remain readable and secrets or raw payloads are never returned.

## 2. Real-Time Revenue and Reconciliation API

- [x] 2.1 Add indexed, bounded repository queries for the current Shanghai natural-day paid, pending, anomalous and closed order counts and amounts.
- [x] 2.2 Add an authorized real-time payment summary endpoint with explicit live-versus-daily-snapshot metadata, timeouts and safe failure responses.
- [x] 2.3 Extend the admin order response with masked callback diagnostics and a bounded pending-reconciliation filter.
- [x] 2.4 Harden the existing Alipay reconciliation command with recent MFA, reason, idempotency and explicit signed-query/order/amount/status checks.
- [x] 2.5 Add Backend tests for successful reconciliation, replay, invalid response signature, unpaid status, wrong order, wrong amount and permission denial.
- [x] 2.6 Add channel acceptance status derived separately from static configuration, enabled state, latest notification validation and latest authoritative query.

## 3. Server Health Sampling and API

- [x] 3.1 Implement independent bounded collectors for application CPU, cgroup/process memory, system load, uptime and aggregate disk usage.
- [x] 3.2 Implement read-only PostgreSQL and Redis health probes plus adapters for API quality and analytics-job freshness.
- [x] 3.3 Add cached current snapshots and recent 60-minute aggregate points without Docker Socket access or sensitive host/process inspection.
- [x] 3.4 Add an `observability.read` server-health endpoint with partial-unavailable states, rate limits and query timeouts.
- [x] 3.5 Add Backend tests for healthy, threshold, unsupported-runtime, probe-timeout, partial-failure, cache and unauthorized scenarios.

## 4. Admin Payment Experience

- [x] 4.1 Add a real-time “今日支付” summary to the operations overview with paid, pending, anomalous and closed amounts plus a clear daily-trend distinction.
- [x] 4.2 Add a pending-reconciliation order view with safe validation-step diagnostics and a recent-MFA, reasoned, per-order authoritative reconciliation action.
- [x] 4.3 Update payment settings to explain AppID and Seller ID/PID roles and show static, enabled, notification and authoritative-query acceptance states independently.
- [x] 4.4 Add loading, stale, partial, empty, success and retry states plus responsive Admin tests for the payment experience.

## 5. Admin Server Monitoring Experience

- [x] 5.1 Add a dedicated “服务器监控” navigation destination without changing user Web routes.
- [x] 5.2 Build responsive resource cards and 60-minute curves for CPU, memory, disk, load and uptime with normal, warning, critical and unavailable states.
- [x] 5.3 Build dependency health cards for Backend, PostgreSQL, Redis, API quality and analytics freshness with isolated retry behavior.
- [x] 5.4 Add Admin tests for complete, partial, stale, unavailable and unauthorized monitoring responses.

## 6. Verification and Rollout

- [x] 6.1 Update payment-channel and commercial-admin operations documentation with diagnostics, reconciliation and monitoring runbooks.
- [x] 6.2 Run focused and full Backend/Admin tests, type checks, production builds, migration checks and strict OpenSpec validation.
- [x] 6.3 Deploy the database migration and Backend first, verify existing user payment and health routes, then deploy Admin without rebuilding Web or desktop companions.
- [ ] 6.4 Use authoritative Alipay queries to reconcile the two confirmed ¥29.90 production orders one at a time and verify idempotent entitlement delivery and ¥59.80 live revenue.
- [ ] 6.5 Verify production server monitoring, payment diagnostics, access controls and responsive Admin layouts, then monitor errors and query latency for one sampling window.
- [x] 6.6 Enforce the official Alipay Seller ID/PID format before activation, expose actionable mismatch diagnostics, and add focused Backend/Admin regressions.
- [x] 6.7 Correct AI success-state analytics, record core answer/realtime usage in the analytics fact source, stop polling after admin-session expiry, and add focused regressions.
