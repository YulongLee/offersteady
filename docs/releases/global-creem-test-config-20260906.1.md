# Global Creem Test configuration 20260906.1

## Scope

- Global Admin can replace Test and Live Creem credentials; values are encrypted at rest and never returned.
- Global Admin can test the selected connection and retrieve the provider's real product catalogue.
- Four paid OfferSteady plans are shown by customer-facing name, price, and billing mode and mapped through selectors.
- Free is explicitly excluded from provider mapping.
- Test and Live credentials, mappings, activation, orders, subscriptions, and events remain isolated.
- The Global customer build is prepared for Creem Test checkout, but the database provider activation remains disabled until credentials and mappings pass and an operator explicitly enables Test.

No Chinese production code or service was deployed. Interview, Companion, ASR, RAG, AI, authentication, and entitlement fulfillment behavior were not changed.

## Verification

- Backend: `524 passed, 20 skipped`.
- Global Admin: `52 passed`; production build passed.
- Global Web: `49 passed`; production Test/Creem build passed.
- Chinese Web production regression build passed.
- OpenSpec `make-global-creem-test-configurable` passed strict validation.
- Overseas `/healthz` and Admin returned HTTP 200; domestic `/healthz` remained HTTP 200.
- Overseas readiness after deployment: Test mode, master switch prepared, provider activation false, credentials absent, mappings absent, `ready=false`.
- Global database migration `0043_global_creem_admin_configuration.sql` applied with encrypted credential and connection-check columns.

## Deployment

- Release: `/opt/offersteady-global/releases/20260906-global-creem-test-config-1`
- Current: `/opt/offersteady-global/current`
- Version: `global-creem-test-config-20260906.1`
- Rollback images:
  - `offersteady-global-backend:rollback-before-creem-test-config-20260906`
  - `offersteady-global-web:rollback-before-creem-test-config-20260906`
  - `offersteady-global-admin:rollback-before-creem-test-config-20260906`

## Operator acceptance

1. Open `https://admin.offersteady.com` and enter 国际商业化.
2. Keep `Test 测试` selected.
3. Save the Test API Key and Test Webhook Secret.
4. Copy the displayed webhook URL to the Creem Test webhook configuration.
5. Click `测试连接并读取商品`.
6. Map Interview Pass, Pro Weekly, Pro Monthly, and Job Hunt to the matching Test products.
7. Confirm all four mappings pass, then explicitly enable Test payment.
8. Use Creem test cards to exercise success and failure cases; do not switch to Live before merchant approval.

## Rollback

Repoint `/opt/offersteady-global/current` to the preceding release and recreate only the Global services with the retained rollback images. Keep the additive database column and all commerce history; never remove the Global PostgreSQL or Redis volumes.
