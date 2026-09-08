# Global Creem commerce

## Scope and safety state

This capability exists only when `OFFERSTEADY_PRODUCT_EDITION=global`. The default remains `cn`, and the domestic catalogue, points, passes, referrals, Alipay, and WeChat Pay tables and routes are unchanged.

New Global checkout has two independent gates:

1. `OFFERSTEADY_GLOBAL_COMMERCE_ENABLED=true` is the deployment-level master gate.
2. The selected Test or Live provider configuration must be explicitly activated after every paid offer has a matching validated Creem Product ID.

Saving a mapping automatically deactivates the selected provider environment. Signed Webhook ingestion must remain reachable when new checkout is disabled so already-created orders can converge.

## Offer catalogue

| Offer code | Customer price | Billing | Benefit summary |
| --- | ---: | --- | --- |
| `global-free` | $0 | One account grant | 15 Copilot minutes and 3 Screen Assist uses |
| `global-interview-pass` | $9.99 | One-time, 24 hours | 180 Copilot minutes, Unlimited Screen Assist, Resume/JD, written exam |
| `global-pro-weekly` | $49.99 | One-time, 7 days | Unlimited full product, Fair Use applies |
| `global-pro-monthly` | $99.99 | Monthly auto-renewal | Unlimited full product, Fair Use applies |
| `global-job-hunt` | $199.99 | One-time, 90 days | Unlimited full product, Fair Use applies |

Published versions are immutable. A purchase creates an entitlement snapshot using the exact plan version fulfilled by the signed provider event.

## Runtime flow

```text
Global Web
  -> POST /api/v1/global-commerce/checkout {offerCode, idempotencyKey}
  -> Backend resolves published USD price + validated Test/Live Product ID
  -> Backend persists pending internal order
  -> Creem checkout is created
  -> Browser redirects to returned HTTPS checkout URL

Creem
  -> POST /api/v1/global-commerce/webhooks/creem (raw body + creem-signature)
  -> HMAC-SHA256 verification
  -> environment/product/reference/amount/currency validation
  -> unique provider event
  -> entitlement fulfillment or lifecycle transition

Browser return page
  -> GET /api/v1/global-commerce/orders/{internalOrderId}
  -> shows Backend-authoritative state
  -> never grants an entitlement from URL parameters
```

Recurring checkout completion enters `confirming`; access is granted only after a verified `subscription.paid` period. Provider-confirmed cancellation keeps the already-paid period through its end. Pause/expiry, refund, and dispute revoke only the matching remaining entitlement, never create negative usage, and never interrupt an interview already in progress. Older reordered subscription events are recorded but cannot regress a newer provider state.

The Global-only Chinese admin area shows readiness, masked secret fingerprints, validated Product mappings, recent redacted orders/subscriptions/Webhook events, refund/dispute counts, and estimated Creem fees. Fair Use reviews store metadata only and can restrict a future session or be cleared by support; interview content is not copied into commerce records.

## Usage authorization

- The first verified Global email login creates the Free grant. Existing accounts receive the same one-time grant lazily on first entitlement read.
- Realtime interview minute reservations consume Copilot minutes.
- Screen Assist reserves one use and releases it after an internal failure.
- Quick Answer inside an already-metered interview does not double-charge the Copilot minute.
- Resume/JD, written exam, and knowledge-base entry points use explicit feature flags.
- Global usage goes through `GlobalUsageBillingAdapter`; it does not read or write domestic billing tables.

## Secret handling

Creem API keys and Webhook secrets are supplied either by the Backend environment or the authenticated Global Admin. Admin-supplied values are encrypted at rest with the server Admin encryption key; environment values remain a fallback. They must never be added to a `VITE_` variable, source file, database plaintext field, JSON response, screenshot, or support log. The Chinese operator view returns only configured/not-configured state and a short one-way fingerprint.

The Global Admin connects to the selected Test or Live API and reads Creem's product catalogue. Operators map the four paid OfferSteady plans through readable selectors; Free has no provider product. A mapping is ready only after the Backend freshly verifies active status, environment, USD amount, and billing type. Saving credentials or a mapping disables that environment until explicit activation.

## Activation checklist

- Legal owner has approved Terms, Privacy, Fair Use, refund policy, auto-renewal text, and support handling.
- Test API key and Webhook secret are present.
- Four paid Test products match amount, USD currency, and one-time/recurring mode.
- Signed Test Webhook delivery is accepted and replay is idempotent.
- Test checkout, renewal, cancellation, refund, dispute, portal, and reconciliation cases pass.
- Live credentials and Live products are configured separately.
- A real low-value Live purchase/refund acceptance passes while general checkout remains disabled.
- General activation receives a separate explicit approval.

## Rollback

First disable new checkout with `OFFERSTEADY_GLOBAL_COMMERCE_ENABLED=false` or the Global admin activation control. Do not disable signed event ingestion for historical orders. If application rollback is required, use the release/image commands recorded in [the baseline](releases/global-creem-commerce-baseline-20260904.md). Additive Global commerce tables are retained for audit and reconciliation.

## Unit economics guardrail

Using Creem's reviewed public fee assumption of 3.9% + $0.40, estimated provider proceeds before taxes, refunds, disputes, and OfferSteady service cost are approximately $9.20, $47.64, $95.69, and $191.79 for the four paid offers. Treat these as estimates only. Before activation, alert thresholds must use measured ASR/LLM/vision cost and provider-confirmed fee data; alerts must never interrupt an active interview.
