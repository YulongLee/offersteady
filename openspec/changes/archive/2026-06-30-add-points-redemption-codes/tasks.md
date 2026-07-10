## 1. Reconcile Billing Specifications and Guidance

- [x] 1.1 Reconcile `add-billing-points-and-passes` with `redemption_credit`, one-wallet behavior and redemption history
- [x] 1.2 Reconcile `improve-growth-checkout-and-user-guidance` with the non-payment redemption entry and safe error guidance
- [x] 1.3 Reconcile `optimize-product-experience-and-distribution` so redemption points do not change catalog prices, rates or margin validation
- [x] 1.4 Update in-app points guidance and relevant privacy/security docs with bearer-secret handling and support recovery
- [x] 1.5 Strictly validate every reconciled active change before modifying implementation behavior

## 2. Protocol and Data Contracts

- [x] 2.1 Add `redemption_credit` and `redemption_reversal` immutable ledger entry kinds
- [x] 2.2 Define normalized redemption request, account-scoped idempotency key and CSRF/authenticated context contracts
- [x] 2.3 Define public result states for redeemed, already redeemed by current user, unavailable, rate limited and temporary failure
- [x] 2.4 Define campaign contracts for points, code limit, points budget, activation window and lifecycle status
- [x] 2.5 Define code records with unique keyed digest, pepper version, public hint and redemption association without plaintext persistence
- [x] 2.6 Define restricted batch generation, one-time export, pause, resume, revoke and reversal commands
- [x] 2.7 Add serialization and compatibility tests proving client-supplied points and plaintext storage fields are absent

## 3. Secure Code Generation and Campaign Management

- [x] 3.1 Define a replaceable cryptographic random-source adapter with at least 80 bits of code entropy
- [x] 3.2 Implement unambiguous code formatting and strict normalization for spaces, hyphens and case
- [x] 3.3 Define a versioned keyed-digest adapter whose pepper remains outside database and client configuration
- [x] 3.4 Generate globally unique digests and non-sensitive public hints with bounded collision retry
- [x] 3.5 Validate positive integer points, code count, total points budget, activation window and policy maximums before campaign creation
- [x] 3.6 Implement campaign draft, active, paused and revoked transitions with immutable audit events
- [x] 3.7 Implement short-lived single-read encrypted export storage and destruction after read or expiry
- [x] 3.8 Reject generation, export and lifecycle commands without `redemption-operator` authorization and recent verification
- [x] 3.9 Add generation tests for entropy source use, normalization collisions, uniqueness, invalid budgets, export replay and authorization

## 4. Atomic Redemption and Wallet Integration

- [x] 4.1 Implement authenticated format and rate-limit checks before keyed-digest lookup
- [x] 4.2 Lock the code and campaign or use equivalent atomic conditional updates during redemption
- [x] 4.3 Validate code state, activation window, campaign state, code count and points budget inside the transaction
- [x] 4.4 Atomically mark the code redeemed, create the user redemption and append one `redemption_credit` ledger entry
- [x] 4.5 Add unique constraints for code redemption and ledger kind/reference to prevent duplicate credit
- [x] 4.6 Roll back code state, campaign counters, redemption record and wallet entry when any transaction step fails
- [x] 4.7 Return the original success result for same-user idempotency replay and same-user code resubmission
- [x] 4.8 Return a generic unavailable result for another account without exposing owner, points, time or campaign details
- [x] 4.9 Preserve membership precedence while making redeemed points available in the existing wallet
- [x] 4.10 Implement authorized fraud reversal through a linked negative ledger entry without rewriting original history or creating an invalid balance
- [x] 4.11 Add concurrent service tests proving exactly one winner and one credit for same-code races
- [x] 4.12 Add transaction tests for wallet failure rollback, replay, expired, future, paused, revoked and exhausted-budget cases

## 5. Abuse Prevention, Privacy and Observability

- [x] 5.1 Implement account-primary and risk-source-secondary redemption rate limits
- [x] 5.2 Add consecutive-failure backoff and safe retry-after responses before code lookup
- [x] 5.3 Detect high-frequency, cross-account and similar-prefix enumeration signals without storing raw codes
- [x] 5.4 Keep user-facing unavailable responses indistinguishable across nonexistent, expired, revoked, other-user-used and exhausted cases
- [x] 5.5 Redact full codes, keyed digests, pepper material, export contents and direct user/network identifiers from logs and errors
- [x] 5.6 Record only safe result categories, latency, campaign budget totals, risk hashes and consistency alerts
- [x] 5.7 Add security tests for unauthenticated requests, CSRF failure, cross-account access, brute force, log redaction and provider-key exposure

## 6. Billing Page Redemption Experience

- [x] 6.1 Add a points redemption card near balance and consumption guidance without entering payment checkout
- [x] 6.2 Add format guidance, accessible input labeling and disabled empty-input state
- [x] 6.3 Submit only the code and generated idempotency metadata; never submit a client-authored points value
- [x] 6.4 Add pending state that prevents duplicate clicks while preserving the existing wallet display
- [x] 6.5 Render redeemed points, new server balance, time and public hint on success and clear plaintext input
- [x] 6.6 Render safe already-redeemed, unavailable, rate-limited and retryable temporary-failure states
- [x] 6.7 Keep failed input only in component memory for correction and remove it on success, route exit or unmount
- [x] 6.8 Insert the new `redemption_credit` record into points history and reload authoritative balance across refresh or another client
- [x] 6.9 Preserve points-pack purchase, membership, official checkout and customer-support behavior
- [x] 6.10 Add component tests for empty, pending, success, replay, unavailable, limit, network failure and keyboard submission states
- [x] 6.11 Add phone, tablet, desktop, zoom, keyboard, screen-reader and 44×44 touch-target checks

## 7. Operations and Audit Experience

- [x] 7.1 Add replaceable administration APIs for campaign creation, activation, pause, resume, revoke, generation and one-time export
- [x] 7.2 Return only safe campaign totals and public hints after plaintext export expires
- [x] 7.3 Add immutable audit records for campaign lifecycle, generation, export, redemption and reversal actions
- [x] 7.4 Keep ordinary support read-only and provide a safe public-hint lookup path without revealing plaintext or keyed digest
- [x] 7.5 Add authorization and audit tests for operator, ordinary support and unauthorized roles

## 8. Verification and Handoff

- [x] 8.1 Use only synthetic redemption codes, users, campaigns and wallet records in tests and fixtures
- [x] 8.2 Run protocol, API and Web tests plus workspace typechecks and production builds
- [x] 8.3 Run browser interaction review for redemption success, safe failures, wallet refresh and existing checkout regression
- [x] 8.4 Scan source, logs, fixtures and built assets for embedded valid-code patterns, plaintext test secrets and pepper material
- [x] 8.5 Check Markdown links and run strict validation for this change and every reconciled active change
- [x] 8.6 Review every capability scenario against implementation and document any production database, KMS or distributed-rate-limit adapter deferred beyond the prototype

