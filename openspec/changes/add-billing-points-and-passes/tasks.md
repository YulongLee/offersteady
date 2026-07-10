## 1. Billing Domain and Catalog

- [x] 1.1 Define typed catalog, SKU, rate, entitlement, wallet, ledger, usage and order contracts
- [x] 1.2 Implement server-managed catalog versions and product snapshots without client-side prices
- [x] 1.3 Add configurable 3-day, 7-day, 15-day and 30-day pass products
- [x] 1.4 Add configurable points packs and initial 5-point answer / 15-point screenshot rates
- [x] 1.5 Add publish, unpublish and margin-threshold validation for catalog items
- [ ] 1.6 Add catalog tests for versioning, price snapshots, invalid products and unpublished products

## 2. Billing Page and Product Experience

- [x] 2.1 Add the protected `/app/billing` route and application-navigation entry
- [x] 2.2 Build the entitlement summary for welcome points, points balance and active-pass expiry
- [x] 2.3 Build the 3/7/15/30-day pass comparison cards with normal-use disclosures
- [x] 2.4 Build points-pack cards and the answer/screenshot rate explanation
- [ ] 2.5 Build order-history, refund-policy and billing FAQ sections
- [x] 2.6 Build configured support-WeChat QR, copy-ID, service-hours and order-consultation entry
- [ ] 2.7 Add billing-page empty, loading, failed, points-user and member states
- [ ] 2.8 Add desktop, tablet, mobile, keyboard and screen-reader tests for the billing page

## 3. Welcome Points and Wallet Ledger

- [x] 3.1 Create an integer points wallet and immutable ledger storage model
- [x] 3.2 Grant one idempotent 200-point welcome transaction after valid account verification
- [x] 3.3 Implement purchase credit, usage reserve, usage settle, usage release, refund and adjustment entries
- [x] 3.4 Implement atomic available-balance and reserved-balance calculation
- [ ] 3.5 Build the user-visible points history with safe descriptions and linked order/usage IDs
- [ ] 3.6 Restrict support adjustments to an approved privileged workflow
- [ ] 3.7 Add ledger tests for duplicate grants, concurrent updates, replay, negative balance and audit history

## 4. Pass Entitlements

- [x] 4.1 Implement pass activation from confirmed-payment time with exact UTC start and end timestamps
- [x] 4.2 Extend repeated pass purchases from the later of now or the current pass end
- [x] 4.3 Implement entitlement precedence so active passes preserve points and bypass per-use deductions
- [ ] 4.4 Record zero-point member usage with estimated cost and no sensitive content
- [ ] 4.5 Implement transparent account, concurrency, safety and abuse limits without hidden point deductions
- [x] 4.6 Preserve already-purchased entitlements when a SKU is changed or unpublished
- [ ] 4.7 Add pass tests for activation, extension, expiry, concurrent purchase and catalog withdrawal

## 5. Usage Reservation and Interview Integration

- [x] 5.1 Generate a unique idempotency key for every answer and screenshot operation
- [x] 5.2 Implement entitlement check and points reservation before creating a paid AI task
- [x] 5.3 Settle ordinary answers at the reserved rate only after a usable answer is delivered
- [x] 5.4 Settle screenshot answers once without stacking the ordinary-answer rate
- [x] 5.5 Release reservations for cancellation, OCR failure, model failure and timeout
- [ ] 5.6 Prevent concurrent operations from reserving more than the available balance
- [x] 5.7 Show active-pass time or points balance in preparation and live-workspace headers
- [ ] 5.8 Show operation price and projected balance next to answer and screenshot confirmation controls
- [x] 5.9 Build insufficient-balance recovery without hiding existing interview content
- [x] 5.10 Add usage tests for retries, duplicate queue messages, failure release, pass precedence and insufficient balance

## 6. Manual WeChat and Alipay Orders

- [x] 6.1 Implement unique orders with product snapshot, amount, channel, expiry and status history
- [x] 6.2 Display only controlled merchant WeChat or Alipay collection configuration for the selected order
- [ ] 6.3 Build payment-proof upload with file limits, malware checks, encryption and transaction-reference fields
- [x] 6.4 Compute proof and transaction fingerprints for duplicate-risk detection
- [x] 6.5 Build user states for awaiting payment, submitted, under review, paid, rejected, expired and refunded
- [ ] 6.6 Build a restricted review queue with merchant-ledger matching fields and audit notes
- [x] 6.7 Activate points or passes exactly once in the same transaction as payment confirmation
- [ ] 6.8 Add reject, resubmit, expiry and refund flows with customer-visible reasons
- [ ] 6.9 Delete proof files according to retention policy while preserving minimal audit metadata
- [x] 6.10 Add security tests for forged proof, duplicate proof, wrong user, wrong amount and repeated approval

## 7. Official Payment Adapter Boundary

- [x] 7.1 Define server-only create-payment, query-payment, notification, refund and reconciliation interfaces
- [x] 7.2 Implement verified notification parsing and signature validation for the selected first provider
- [ ] 7.3 Implement active server-side order query before automated entitlement activation
- [x] 7.4 Make repeated callbacks and order queries idempotent
- [ ] 7.5 Add provider sandbox tests for success, cancellation, delayed notification, forged notification and refund
- [x] 7.6 Document migration from manual proof review to official merchant payment confirmation

## 8. Customer Support and Billing Administration

- [x] 8.1 Store support WeChat ID, QR asset, service hours and refund text in controlled server configuration
- [ ] 8.2 Build customer order lookup and support handoff using order numbers instead of public proof sharing
- [ ] 8.3 Separate customer-support, payment-review, refund and wallet-adjustment permissions
- [ ] 8.4 Add immutable audits for approval, rejection, refund, pass adjustment and points adjustment
- [ ] 8.5 Redact screenshots, transaction references, payment identities and wallet internals from ordinary logs
- [ ] 8.6 Add privileged-action tests for unauthorized access, role separation and audit completeness

## 9. Profitability, Privacy and End-to-End Verification

- [ ] 9.1 Record per-operation model, speech, storage, payment and review cost estimates without content
- [ ] 9.2 Build aggregated revenue, refund, cost and gross-margin reporting by SKU and entitlement type
- [x] 9.3 Alert and prevent new publication when projected margin is below the configured threshold
- [ ] 9.4 Verify payment-proof access control, encryption, retention and deletion behavior
- [ ] 9.5 Run the 200-point signup, ordinary answer, screenshot answer and insufficient-balance journey
- [ ] 9.6 Run pass purchase, activation, unlimited-use, extension and expiry journeys
- [ ] 9.7 Run manual WeChat/Alipay order, proof, review, activation, rejection and refund journeys
- [ ] 9.8 Verify all specification scenarios with synthetic payment data and document deferred provider behavior
