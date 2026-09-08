# Global preview 2026-09-04.1

## Deployment

- Public URL: `https://offersteady.com`
- Alternate hostname: `https://www.offersteady.com`
- Host: `47.84.65.103`
- Compose project: `offersteady-global`
- Source bundle: `/opt/offersteady-global/releases/20260904-global-preview-2`
- Release marker: `global-preview-20260904.1:uncommitted-source-bundle`
- Nginx backup: `/opt/offersteady-global/backups/nginx-before-offersteady-20260904-1350.tgz`
- Certificate expiry at deployment: 2026-12-03, with Certbot automatic renewal enabled

The deployment is isolated from the Chinese production database, Redis, host, domain, runtime, secrets, and release artifacts. Existing services on the overseas host remained active. The Global Admin build is loopback-only at `127.0.0.1:18881`.

## Verification

- Global Web tests: 20 passed.
- Global and Admin production builds passed.
- OpenSpec strict validation and deployment static isolation checks passed.
- Root, login, help, legal, application, interview creation, written exam, library, billing, device, settings, health, build-manifest, and Web-state routes returned HTTP 200.
- Build manifest reports Global edition, `en-US`, same-origin API, and commerce disabled.
- Backend is healthy in production mode with zero Global users and zero Global interviews after schema bootstrap.
- PostgreSQL and Redis expose no host ports; Web, Backend diagnostics, and Admin bind to loopback only.
- Domestic production health remained HTTP 200 and pre-existing overseas host services stayed active.

## Current launch status

This is a technical preview, not a commercial international launch. International authentication/OTP, Global-specific provider accounts and data residency, payment/currency/tax/refund/legal flows, protected Admin access, and signed/notarized Global desktop releases remain open blockers.
