## 1. Device center backend and Web

- [x] 1.1 Add repository support and authenticated API for listing the current account's linked desktop devices
- [x] 1.2 Return masked identity, platform, last activity, online, permission/capability and active-interview summaries independently
- [x] 1.3 Replace the fixed device-page fixture with loading, empty, error, refresh and truthful device states
- [x] 1.4 Add per-device diagnostic details and guide recovery links without starting capture or requesting browser permissions
- [x] 1.5 Add backend and Web regression tests for account isolation, online/offline state, empty state, refresh and diagnostics

## 2. Referral persistence and API

- [x] 2.1 Add referral configuration, stable user code, activation relationship and referral ledger migration
- [x] 2.2 Implement authenticated referral status, code resolution and one-time activation services
- [x] 2.3 Make activation, configuration snapshot and inviter ledger credit atomic and concurrency safe
- [x] 2.4 Enforce invalid-code, disabled, self-referral, same-code replay and different-code rejection outcomes
- [x] 2.5 Add backend tests for stable links, privacy, idempotency, concurrency, rollback and balance/ledger updates

## 3. Referral Web and Admin experience

- [x] 3.1 Add the billing referral card with share-link generation, copy feedback, reward amount, invite count and total rewards
- [x] 3.2 Add the public referral landing route and authenticated pending-activation recovery flow
- [x] 3.3 Add Admin growth settings APIs, `growth.manage` authorization, validation, versioning and audit events
- [x] 3.4 Add Admin growth settings UI with effective status, enable switch, reward amount and required change reason
- [x] 3.5 Add Web and Admin tests for activation outcomes, copy state, configuration validation and permission gates
- [x] 3.6 Add a Billing-page activation form that accepts a referral URL or code and refreshes authoritative status after activation
- [x] 3.7 Add Web regression tests for URL/code parsing, success, invalid input, self-referral and already-activated states

## 4. Verification and release

- [x] 4.1 Run focused and full Backend, Web and Admin tests, typechecks and production builds
- [x] 4.2 Validate the OpenSpec change strictly and review privacy/security scenarios
- [x] 4.3 Commit and push the completed change
- [x] 4.4 Deploy database/backend first, then Web and Admin without rebuilding the desktop assistant
- [ ] 4.5 Run production API and Playwright smoke checks for device center, referral activation and Admin configuration
  - Production API, route and bundle smoke checks passed; the Playwright browser runtime had no available browser instance in this session.
- [x] 4.6 Re-run focused Web tests, typecheck/build and strict OpenSpec validation for the Billing activation entry
