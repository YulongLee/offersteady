## 1. Baseline and edition isolation

- [x] 1.1 Record current Global Web/Backend/Admin/database releases, production health, migration version, and exact rollback commands without changing running services
- [x] 1.2 Add a fail-closed `cn|global` Backend product-edition setting, set only the Global Compose deployment to `global`, and add domestic isolation tests
- [x] 1.3 Add shared Global commerce protocol types without changing existing domestic billing/payment contracts

## 2. Global catalogue and persistence

- [x] 2.1 Add additive migrations for Global plan versions, provider mappings, orders, provider events, subscriptions, entitlements, usage reservations, Free grants, and fair-use decisions
- [x] 2.2 Seed the five approved offer codes, USD prices, billing modes, durations, quotas, features, display order, and Pro Weekly featured state
- [x] 2.3 Implement a Global catalogue repository/service with immutable published versions, validation, publication, and purchased-benefit snapshots
- [x] 2.4 Add migration and repository tests proving uniqueness, idempotency, immutable purchase snapshots, and no access to domestic tables
- [x] 2.5 Publish catalogue version 2 with Interview Day Pass and the approved $49.99/$99.99/$199.99 prices, preserve version 1 purchase snapshots, and invalidate Creem readiness until the new amounts are revalidated

## 3. Entitlements, usage, and fair use

- [x] 3.1 Grant Free once on verified Global email registration and lazily backfill existing Global accounts under a database uniqueness constraint
- [x] 3.2 Implement active Global entitlement resolution, one-time pass stacking, provider-period Monthly renewal, expiry, and feature flags
- [x] 3.3 Implement atomic Copilot-minute and Screen-Assist reservation, settlement, release, remaining-usage, and retry idempotency
- [x] 3.4 Integrate Global entitlement authorization into existing interview, Screen Assist, written-exam, Resume/JD, and knowledge-base entry points without changing their processing behavior
- [x] 3.5 Implement metadata-only fair-use signals, one-active-interview protection, durable future-session restrictions, support review, and the no-active-session-interruption invariant
- [ ] 3.6 Add synthetic tests for Free exhaustion, paid benefits, Unlimited behavior, failure release, concurrency, stacking/renewal, fair-use review, and domestic regression

## 4. Creem provider lifecycle

- [x] 4.1 Define the replaceable international-commerce provider port and implement Creem Test/Live API clients with bounded timeouts, redaction, safe retries, and circuit protection
- [x] 4.2 Implement authenticated idempotent checkout creation using internal offer codes and validated server-owned Creem product mappings
- [x] 4.3 Implement raw-body HMAC-SHA256 webhook verification, business-fact validation, unique provider-event persistence, and transactional fulfillment
- [x] 4.4 Implement one-time checkout, Monthly subscription paid/canceled/paused/expired, refund, dispute, duplicate, and reordered-event state transitions
- [ ] 4.5 Implement authenticated customer-portal creation plus bounded single-order/subscription and scheduled reconciliation
  - Customer portal and an audited, bounded single-order/subscription reconciliation action are implemented; scheduled reconciliation remains open.
- [ ] 4.6 Add contract fixtures and synthetic tests for checkout failures, forged redirects, invalid signatures, mismatches, replay, missed delivery, renewal, cancellation, refund, dispute, and reconciliation
  - Current official Product/Checkout/Webhook shapes, replay, missed one-time delivery, renewal, scheduled cancellation, refund, and dispute have synthetic coverage; broader provider acceptance fixtures remain open.

## 5. Global commerce administration

- [ ] 5.1 Add Global-edition admin APIs for plan drafts/versions, provider mappings/readiness, activation, orders, subscriptions, events, reconciliation, refunds, disputes, fair-use reviews, and unit economics
- [x] 5.2 Add permissions, recent-MFA confirmation, rate limits, secret masking/fingerprints, immutable audit records, and automatic deactivation after sensitive changes
- [ ] 5.3 Build the Chinese Global-commerce admin views for plan configuration, Creem Test/Live readiness, Webhook health, operational diagnostics, and order/subscription support
- [ ] 5.4 Add provider-fee/net-revenue, measured service-cost, gross-margin, refund/dispute, webhook-lag, and anomaly alerts without storing interview content
- [ ] 5.5 Add admin API/component tests for authorization, validation, masking, activation gates, diagnostics, reconciliation, audit, responsive layout, and Chinese-edition hiding
- [x] 5.6 Add a Global-only member workspace with bounded email/name/ID search, member detail, idempotent manual plan grants, targeted entitlement revocation, audit, and API/component regression tests

## 6. Global pricing and billing experience

- [x] 6.1 Replace the read-only Global account placeholder with English pricing cards and comparison content for the five approved offers
- [x] 6.2 Add explicit one-time/auto-renewal, USD/final tax-currency, refund, Fair Use, Terms, Privacy, and support disclosures at the correct decision points
- [x] 6.3 Add checkout creation/redirect and Backend-authoritative return states with bounded polling, duplicate-click protection, retry, and support handling
- [x] 6.4 Add current plan, expiry/cancellation, metered remaining usage, Unlimited status, feature access, billing history, and customer-portal management
- [ ] 6.5 Add desktop/tablet/mobile, keyboard, screen-reader, empty/loading/error/provider-outage, and product-copy regression coverage

## 7. Release verification

- [ ] 7.1 Run migrations and full Global Backend/protocol/Web/Admin test, typecheck, build, security, and copy-audit suites using only synthetic commerce data
- [ ] 7.2 Run domestic Backend/Web/Admin/payment/referral/interview regression suites and prove no Chinese production configuration, bundle, data, or runtime behavior changed
- [ ] 7.3 Validate fixed-price provider-fee estimates and measured ASR/LLM/vision unit-cost reporting, then document commercial margin thresholds for review
- [ ] 7.4 Complete real-browser Global pricing, checkout-state, account, and admin visual/accessibility passes at supported viewports
- [ ] 7.5 Run strict OpenSpec validation and update Global architecture, environment, operations, incident, refund, Fair Use, reconciliation, and rollback documentation

## 8. Staged activation

- [x] 8.1 Deploy additive migrations and dormant Global Backend/Admin/Web changes with checkout disabled; verify Global and Chinese production health
- [ ] 8.2 After credentials are supplied, configure Creem Test products/secrets/webhook and pass real Test checkout, renewal, cancellation, refund, duplicate-event, portal, and reconciliation acceptance
- [ ] 8.3 After legal and explicit release approval, configure isolated Live products/secrets/webhook and pass one real low-value purchase/refund acceptance without enabling general checkout
- [ ] 8.4 After separate activation approval, enable Global Live checkout, monitor commercial/security SLOs, and retain one-action rollback that disables new checkout while preserving event ingestion
