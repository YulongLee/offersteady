# Global remove User Manual release 20260904.1

## Deployment

- Host: `47.84.65.103`
- Public URL: `https://offersteady.com`
- Release: `global-remove-user-manual-20260904.1`
- Release path: `/opt/offersteady-global/releases/20260904-global-remove-user-manual-1`
- Compose project: `offersteady-global`
- Scope: Global Web only; Backend, Admin, PostgreSQL, Redis, and Chinese production were not restarted
- Global commerce: disabled
- Provider exposed to browser: `none`
- Web image: `sha256:786ca938ac1359f15d15eebc38d0ee19c5e282896731cb4c77c89cf01e0d5c07`

## Acceptance

- Removed the external `User manual` navigation entry from Global desktop and mobile navigation.
- Retained the in-product `Product guide` route.
- Global test, typecheck, production build, and strict OpenSpec validation passed before deployment.
- Global `/healthz`, `/`, `/login`, `/app`, `/app/guide`, `/api/v1/web/state`, and the `www` hostname returned HTTP 200 after deployment.
- The public build manifest reports `productEdition=global`, `locale=en-US`, `commerceEnabled=false`, and `commerceProvider=none`.
- Both Chinese production health endpoints returned HTTP 200 after the Global Web deployment.

## Rollback

The previous source release remains at `/opt/offersteady-global/releases/20260904-global-commerce-dormant-1`. The previous Web image is retained as:

- `offersteady-global-web:rollback-before-remove-user-manual-20260904`
- Image ID: `sha256:8ce0e5f968b335d5e620f816ca9c71007a6a680eae1d102c9adb200625b5f5c5`

Rollback must recreate only the Global `web` service from the retained image/release. Do not restart Global data services, remove volumes, or modify Chinese production.
