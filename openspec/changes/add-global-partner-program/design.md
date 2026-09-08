## Context

OfferSteady Global is deployed independently at `offersteady.com` with its own Web build, Compose project, PostgreSQL, Redis and Chinese operator console. Global commerce is intentionally dormant while Creem review is incomplete. The Chinese product now has a first-level partner program, but its SMS identities, CNY orders, Alipay/WeChat payout profiles and domestic database cannot be reused by Global.

The current Global implementation exists locally and in overseas production but is not yet tracked in the repository baseline. That must be corrected before feature work so the release is reviewable and rollback is deterministic.

## Goals / Non-Goals

**Goals:**

- Add a commercially understandable English partner acquisition loop at the bottom of the Global homepage.
- Preserve a server-authoritative link → verified registration → confirmed Creem order → commission → manual settlement chain.
- Give partners a private English dashboard and Global operators a Chinese reconciliation console with runtime control.
- Keep all Global data and deployment isolated from China production and outside interview/AI hot paths.

**Non-Goals:**

- Automatic payouts, tax withholding, tax forms, bank-account verification or identity-document collection.
- Multi-level marketing, self-referral, coupon creation or partner access to referred-user identity.
- Generating commission from a checkout redirect, pending order or unverified Creem event.
- Activating Creem checkout or modifying any Chinese product/runtime as part of this change.

## Decisions

### 1. Establish a Global Git baseline before implementation

First commit the currently deployed Global files and record the overseas release marker, image identifiers and rollback command. Feature work then starts from that exact baseline in an isolated branch. This is safer than copying the untracked Global tree into a clean branch piecemeal, which could silently omit deployed behavior.

### 2. Use Global-specific partner tables and routes

Introduce Global-prefixed partner profiles, attribution claims, commission ledger, payout profiles, payout requests and runtime settings in the Global database. Global APIs require `OFFERSTEADY_PRODUCT_EDITION=global`; domestic APIs and tables remain untouched. Sharing one schema implementation with edition columns was rejected because a configuration error could cross financial boundaries.

### 3. Couple commission projection to authoritative commerce facts, not checkout execution

Commission projection reads immutable, provider-confirmed Global order/refund/dispute facts after Creem webhook validation and writes idempotent ledger entries asynchronously or through a bounded projection. It is not added to the synchronous webhook transaction, browser redirect or interview paths. While Creem is dormant, visit and registration attribution works but financial balances stay zero.

### 4. Keep public copy simple and put accounting rules in the protected page

The homepage says `Share OfferSteady and earn 20% referral commission.` The partner page explains eligibility, refund/dispute reversals, attribution windows, prohibited conduct and manual settlement. The entry appears only at the public homepage bottom and never in workbench navigation.

### 5. Make payout methods configurable and manual-only

The domain stores a method code, encrypted recipient name and encrypted provider identifier with masked display values. Initial allowed methods can be PayPal and/or Wise based on the final operational decision; no bank-card or identity-document fields are implemented. This avoids hard-coding a provider before OfferSteady confirms that it can legally and operationally pay recipients in the US, UK, Australia and Canada.

### 6. Use append-only USD accounting and request-bound payout versions

Earnings, reversals, reserves, releases and payments are immutable cents-based USD ledger entries. Settlement requests bind the payout-profile version selected at request time. Administrators cannot directly zero a balance; they approve/reject requests and record a real manual payment reference.

### 7. Add a database runtime switch under the deployment master gate

Global operations can pause public discovery and new enrollment without a deployment. The deployment-level environment flag remains a fail-closed master gate. Pausing never deletes historical links or financial records and does not block reconciliation or already-submitted settlement work.

## Risks / Trade-offs

- [Global source is not currently versioned] → Capture and verify the deployed baseline before any implementation commit.
- [Creem review is incomplete] → Permit acquisition attribution but create no revenue or commission without signed confirmed order facts.
- [Cross-border payout/tax obligations vary] → Keep payouts manual, minimize data, disclose operator review and confirm payout methods/legal handling before activation.
- [Refunds or disputes occur after settlement] → Append negative reversals and carry the balance forward; never erase paid history.
- [Partner reporting loads the database] → Use bounded pagination, indexed aggregates, independent query budgets and asynchronous projection outside product hot paths.
- [20% could compress margins] → Report commission against provider-confirmed net eligible receipts and monitor provider fees plus AI cost before enabling broad recruitment.

## Migration Plan

1. Inventory overseas production and commit the current Global implementation as a rollback baseline without deploying China.
2. Add Global-only migrations, Backend services and APIs behind disabled master/runtime gates.
3. Add the Global Web entry/dashboard and Chinese Global-admin views; keep activity disabled in production.
4. Run Global suites plus explicit domestic source/build isolation checks using synthetic data.
5. Deploy only to the overseas Compose project during a safe window and validate health, attribution and admin controls with finance projection disabled.
6. Enable public recruitment only after payout methods, agreement text and manual operating process are approved. Creem commission projection remains dormant until signed payment lifecycle acceptance passes.
7. Roll back application images and disable recruitment if needed; retain additive financial/audit tables and never delete volumes.

## Open Questions

- Which initial manual payout method(s) can OfferSteady reliably operate: PayPal, Wise, or both?
- What minimum USD payout threshold and monthly cutoff should apply? A configurable value is required before activation.
- Should commission basis exclude Creem fees in addition to tax, refunds, disputes and chargebacks? Finance/legal confirmation is required before financial activation.
