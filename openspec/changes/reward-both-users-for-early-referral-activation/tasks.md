## 1. Persistence and compatibility

- [x] 1.1 Add a forward-only migration for inviter/invitee reward configuration, activation snapshots and `referral_invitee_credit` ledger support
- [x] 1.2 Update every billing schema initializer and repository model so startup order cannot remove the new ledger kind or defaults
- [x] 1.3 Preserve existing `rewardPoints` API compatibility while exposing explicit inviter and invitee rewards

## 2. Eligibility and atomic rewards

- [x] 2.1 Derive the activation deadline from the authenticated account's server-side registration timestamp using an inclusive 72-hour boundary
- [x] 2.2 Return authoritative eligibility, deadline and stable ineligibility reason fields from referral status and activation APIs
- [x] 2.3 Extend the activation transaction to lock both users in stable order and atomically write the relation plus one unique reward ledger entry per user
- [x] 2.4 Preserve self-referral rejection, lifetime single activation, replay idempotency, activity disablement and privacy boundaries
- [x] 2.5 Add backend regressions for before/at/after deadline, missing legacy timestamps, both balances, both ledgers, replay, concurrency and rollback

## 3. Admin growth configuration

- [x] 3.1 Extend growth settings APIs and audit records with separately validated inviter and invitee reward amounts
- [x] 3.2 Update the Admin growth settings UI to edit both reward amounts and explain the fixed three-day activation window
- [x] 3.3 Add Admin permission, validation, persistence and rendering regressions

## 4. User referral experience

- [x] 4.1 Show the inviter and new-user rewards, activation deadline and remaining eligibility in the Billing referral card
- [x] 4.2 Disable activation after expiry and show a clear three-day-window explanation based on the server reason code
- [x] 4.3 Refresh balances, referral status and point details after successful activation so both rewards are immediately visible
- [x] 4.4 Add Web regressions for eligible, boundary countdown, expired, successful mutual reward and already-activated states

## 5. Verification and release readiness

- [x] 5.1 Run focused and full Backend, Web and Admin tests, typechecks and production builds
- [x] 5.2 Validate this OpenSpec change strictly and review migration, idempotency, privacy and abuse scenarios
- [x] 5.3 Prepare database-first deployment and rollback notes; do not deploy until explicitly authorized
