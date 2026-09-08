# Global Creem commerce dormant release 20260904.1

## Deployment

- Host: `47.84.65.103`
- Public URL: `https://offersteady.com`
- Release: `global-commerce-dormant-20260904.1`
- Release path: `/opt/offersteady-global/releases/20260904-global-commerce-dormant-1`
- Compose project: `offersteady-global`
- Global commerce: disabled
- Provider exposed to browser: `none`
- Database migration: 10 isolated `global_commerce_*` tables present

Deployed image IDs:

- Web: `sha256:8ce0e5f968b335d5e620f816ca9c71007a6a680eae1d102c9adb200625b5f5c5`
- Backend: `sha256:b5f348fe90813bf36b281beb99bf47bdfb80d3a441cd564e1476c1f1bef87cdf`
- Admin: `sha256:afd54fac5da462d9472ffbe8e44e7ab971b915ddaf3e07a34abe249af6ab3f70`

## Acceptance

- Global loopback and public health checks passed.
- `/`, `/account`, `/guide`, and `/api/v1/web/state` returned HTTP 200.
- The public build manifest reports the expected release, `productEdition=global`, `locale=en-US`, `commerceEnabled=false`, and `commerceProvider=none`.
- The Global catalogue returned all five approved plan versions.
- Backend runtime reports `OFFERSTEADY_PRODUCT_EDITION=global` and `OFFERSTEADY_GLOBAL_COMMERCE_ENABLED=false`.
- Global Backend logs contained no traceback, exception, or error during acceptance.
- Chinese production health remained successful after the Global deployment.

## Rollback

The prior release remains at `/opt/offersteady-global/releases/20260904-global-complete-1`. The pre-release images are retained as:

- `offersteady-global-web:rollback-before-commerce-20260904`
- `offersteady-global-backend:rollback-before-commerce-20260904`
- `offersteady-global-admin:rollback-before-commerce-20260904`

Rollback must recreate only the Global services with those images or the prior release Compose configuration. Do not remove the PostgreSQL or Redis volumes. The additive Global commerce tables remain dormant and retained for audit.
