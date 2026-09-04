## 1. Data protection and migration

- [x] 1.1 Add additive payout-profile version storage, settlement-profile references, constraints and reconciliation indexes
- [x] 1.2 Add dedicated payout encryption configuration, production fail-closed validation and masked-value helpers
- [x] 1.3 Add key-version and retention-ready metadata without logging or exporting plaintext payout data

## 2. Backend payout profile capability

- [x] 2.1 Implement active-partner payout-profile create/update and masked read operations
- [x] 2.2 Bind new settlement requests atomically to the selected immutable payout-profile version
- [x] 2.3 Add user payout-profile APIs with strict validation, no-store responses and feature isolation
- [x] 2.4 Add single-request administrator reveal with payout permission, recent MFA, no-store response and success/failure audit

## 3. Reconciliation capability

- [x] 3.1 Implement bounded aggregate order, commission, reversal, reserved and settled KPI queries
- [x] 3.2 Implement paginated commission-order reconciliation with state/date filters and no referred-user PII
- [x] 3.3 Extend settlement-list responses with masked payout target, timestamps, payment reference and linked ledger totals
- [x] 3.4 Add administrator reconciliation APIs while preserving separate read and payout-management permissions

## 4. User and administrator experience

- [x] 4.1 Add the emphasized responsive partner-program card to authenticated side navigation without changing interview navigation behavior
- [x] 4.2 Add the partner payout-profile form, masked saved state and manual-settlement explanation
- [x] 4.3 Add partner KPI cards, commission-order filters/table and richer settlement lifecycle to the admin promotion center
- [x] 4.4 Keep reveal and mutation controls hidden from read-only administrators and require explicit confirmation for sensitive actions

## 5. Verification and rollout

- [x] 5.1 Add migration and repository tests for encryption, masking, version history and immutable settlement binding
- [x] 5.2 Add API permission, recent-MFA, no-store, audit and plaintext-leak regression tests
- [x] 5.3 Add Web/Admin responsive navigation, form, reconciliation-state and read-only permission tests
- [x] 5.4 Run backend suites, frontend tests/typechecks/builds, secret scans and strict OpenSpec validation
- [x] 5.5 Document payout-data access, manual reconciliation, retention, key rotation, rollout and rollback procedures
- [x] 5.6 Deploy with payout-profile collection disabled, configure the dedicated production key, verify a synthetic end-to-end flow, then enable without restarting interview data services

## 6. Correct partner discovery and activity control

- [x] 6.1 Remove the partner-program entry and styling from desktop and mobile authenticated workbench navigation
- [x] 6.2 Add an additive versioned runtime activity setting with public read and audited administrator update APIs
- [x] 6.3 Make the homepage bottom entry and new enrollment follow the runtime activity setting without changing historical partner accounting
- [x] 6.4 Add Web, Admin and Backend regression tests for entry scope, permissions, toggle behavior and historical-data preservation
- [x] 6.5 Run focused and full relevant test/typecheck/build suites plus strict OpenSpec validation
- [x] 6.6 Deploy during a zero-active-interview window and verify the homepage, workbench, admin switch and existing settlement data

## 7. Homepage copy and enrolled-partner availability regression

- [x] 7.1 Simplify the public homepage partner copy while keeping detailed accounting rules on the activity page
- [x] 7.2 Fix the enrolled-partner dashboard balance query parameter mismatch and add regression coverage
- [x] 7.3 Run focused verification, deploy during a zero-active-interview window and verify the production partner page

## 8. Partner user and admin availability hotfix

- [x] 8.1 Apply private-response cache headers through FastAPI's response object instead of the API envelope
- [x] 8.2 Correct the administrator reconciliation summary parameter binding and add endpoint regression coverage
- [ ] 8.3 Run focused verification and deploy the Backend-only hotfix after confirming no active interviews
