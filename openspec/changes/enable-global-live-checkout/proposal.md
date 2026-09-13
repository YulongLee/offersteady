## Why

Global Commerce and Creem Live are approved and ready, but the public pre-rendered homepage and pricing page still say checkout is unavailable and render disabled paid-plan controls. This contradicts the live product and prevents visitors who have not signed in from reaching the normal purchase flow.

## What Changes

- Update the Global public pricing catalogue and generated HTML to describe live checkout accurately.
- Link paid-plan calls to action to the existing Global sign-in flow so authenticated users can continue into the existing Creem checkout.
- Remove stale “provider approval” and disabled-control language from public SEO metadata and structured data.
- Keep the existing backend checkout, webhook, entitlement, and authentication behavior unchanged.

## Capabilities

### New Capabilities
- `global-live-checkout-entry`: Public Global pages expose an accurate entry point to the approved live checkout flow.

### Modified Capabilities
- None.

## Impact

- `apps/web-global/src/public-review-pages.json` and generated public HTML.
- Global public-page regression tests and deployment verification.
- No API, database, payment-provider, or domestic-edition changes.
