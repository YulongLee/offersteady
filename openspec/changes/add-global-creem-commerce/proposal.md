## Why

OfferSteady Global has a production customer experience but no purchasable international plans, provider lifecycle, or Global-specific operator controls. A commercial launch for the US, UK, Australia, and Canada needs transparent USD offers, durable entitlements, and a Creem Merchant-of-Record integration that cannot grant access from an unverified browser redirect or affect the Chinese product.

## What Changes

- Add a server-managed Global catalogue with five offers: a one-time Free grant, one-time Interview Day Pass, one-time Pro Weekly, recurring Pro Monthly, and one-time Job Hunt pass.
- Grant the Free allowance once per account: 15 Copilot minutes and 3 Screen Assist uses.
- Give Interview Day Pass 180 Copilot minutes plus unlimited Screen Assist and Resume/JD access for 24 hours; give the three Pro offers full-feature access under a clearly disclosed fair-use policy.
- Add Global plan-entitlement and usage accounting that is independent from domestic points and time-pass semantics, snapshots purchased benefits, and never interrupts an already-running interview because of an automated fair-use decision.
- Add server-side Creem checkout creation, signed webhook processing, provider-event idempotency, subscription lifecycle synchronization, refund/dispute handling, reconciliation, and customer-portal access.
- Add a Chinese-language international-commerce section to the operator console for plan publication, presentation, benefit versions, Creem product mappings, Test/Live readiness, webhook health, orders, subscriptions, refunds, and audit history.
- Replace the disabled Global account placeholder with an English pricing, checkout-return, entitlement, usage, billing-history, and subscription-management experience.
- Keep Creem secrets server-only and keep both provider mode and customer purchasing disabled until explicit Test and Live activation gates pass.
- Keep the Chinese Web, domestic catalogue, domestic payment channels, referral behavior, interview/audio/screenshot behavior, and desktop companion unchanged.

## Capabilities

### New Capabilities

- `global-plan-catalog-and-entitlements`: Defines Global offers, one-time Free eligibility, purchased benefit snapshots, usage accounting, stacking/renewal rules, and fair-use behavior.
- `creem-checkout-and-lifecycle`: Defines secure Creem checkout, webhook, subscription, refund, dispute, reconciliation, and customer-portal behavior.
- `global-commerce-admin-operations`: Defines Chinese operator controls, secret boundaries, activation gates, diagnostics, auditing, and rollback for international commerce.
- `global-pricing-and-billing-experience`: Defines the customer-facing English pricing, checkout return, plan status, usage, billing history, and subscription-management experience.

### Modified Capabilities

<!-- No current main capability changes. Global commerce is added behind an explicit product-edition boundary. -->

## Impact

- Affects `apps/backend` billing/provider modules, Global-only database tables and migrations, Global runtime configuration, `apps/web-global`, `apps/admin`, shared billing protocol types, tests, deployment manifests, and commerce documentation.
- Adds outbound server-to-server Creem API traffic and a public HTTPS webhook endpoint; secrets and raw webhook payloads remain outside browser bundles and ordinary logs.
- Uses the isolated Global PostgreSQL database and overseas deployment. Migrations may define dormant tables in other environments, but domestic runtime paths remain selected by the Chinese product edition and do not read or write Global commerce state.
- Does not persist interview audio, screenshots, transcripts, resumes, or JD content as part of payment processing. Provider/customer identifiers and billing records are retained only for commerce, support, reconciliation, and legal obligations.
