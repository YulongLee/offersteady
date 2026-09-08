# Global Creem hardening 20260906.1

## Deployment

- Host: `47.84.65.103`
- Domain: `https://offersteady.com`
- Release path: `/opt/offersteady-global/releases/20260906-global-creem-hardening-1`
- Release version: `global-creem-hardening-20260906.1`
- Commerce remains dormant: server and Web checkout switches are disabled.

## Changes

- Added the production-safe `/billing/success` return route with no-store and no-index headers.
- Made checkout return, webhook, and legal URLs visible through readiness diagnostics.
- Updated the Creem adapter and webhook parser for current product, checkout, subscription, refund, and dispute payload shapes.
- Added `trialing`, `past_due`, `unpaid`, and `subscription.update` lifecycle handling without granting unpaid access or revoking an already-paid period.
- Made provider-event persistence, entitlement fulfillment, order updates, and subscription updates one transaction.
- Added exact-payload retry and bounded order reconciliation coverage.

## Verification

- Payment-focused Backend tests: 32 passed before the final lifecycle tests; final checkout/migration suite: 22 passed.
- Global Web: 49 tests passed; production build passed.
- Global Admin: 47 tests passed; production build passed.
- Workspace TypeScript typecheck passed.
- Backend full suite: 516 passed, 20 skipped. Two unrelated ASR wall-clock threshold cases exceeded their limit under concurrent build load and both passed immediately when rerun alone.
- Strict OpenSpec validation and Global deployment-asset validation passed.
- Production health, login, admin, legal pages, pricing, readiness, and `/billing/success` returned HTTP 200.
- Migration `0042_global_creem_lifecycle_hardening.sql` is recorded on production; recent Backend error scan returned zero.
- Chinese production health remained HTTP 200 and no Chinese deployment was changed.

## Remaining activation gates

Real checkout remains unavailable until Creem supplies/approves the environment and operators configure the corresponding API key, webhook secret, and four validated Product mappings. Test and Live payment acceptance must be completed before either checkout switch is enabled.

## Rollback

The preceding release remains `/opt/offersteady-global/releases/20260906-global-companion-1217`. Pre-cutover images are retained as:

- `offersteady-global-backend:rollback-before-creem-hardening-20260906`
- `offersteady-global-web:rollback-before-creem-hardening-20260906`
- `offersteady-global-admin:rollback-before-creem-hardening-20260906`

Rollback must preserve the Global PostgreSQL and Redis volumes. The lifecycle migration is additive and compatible with the preceding application version.
