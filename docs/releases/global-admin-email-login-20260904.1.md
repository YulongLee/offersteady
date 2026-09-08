# Global Admin email login release 20260904.1

## Deployment

- Public entry: `https://admin.offersteady.com`
- Release: `global-admin-email-20260904.1`
- Release path: `/opt/offersteady-global/releases/20260904-global-admin-email-1`
- Scope: Global Admin image only; deployment occurred with zero active Global interviews
- Current Admin image: `sha256:e2462f5720daf2352f7052b87e04636aa0b3d8d9929e6068af489ce492ffb16d`
- Rollback Admin image: `sha256:afd54fac5da462d9472ffbe8e44e7ab971b915ddaf3e07a34abe249af6ab3f70`

## Behavior

- The Global Admin uses the existing Global email verification-code APIs.
- The domestic Admin retains its existing phone/SMS login behavior.
- A verified operator-approved Global email identity was authorized as the first active `super_admin` through a server-side bootstrap and an audit event was recorded.
- The approved identity, verification codes, access tokens, Admin tokens, and enrollment secret are not stored in source or this release record.

## Acceptance

- Admin unit/UI tests: 47 passed.
- Backend email authentication and Admin authorization tests: 22 passed.
- Admin typecheck, domestic build, Global build, and strict OpenSpec validation passed.
- The deployed Global Admin bundle contains the email login UI and email send-code endpoint.
- `https://admin.offersteady.com/` returned HTTP 200 and anonymous `/api/v1/admin/session` returned HTTP 401.
- Global and Chinese production health endpoints returned HTTP 200.
- Final browser login with the approved mailbox remains an operator acceptance step because the verification code is never read by deployment tooling.

## Rollback

Retag `offersteady-global-admin:rollback-before-email-login-20260904` as `offersteady-global-admin:latest` and recreate only the Global `admin` service. Do not restart the Global Web, Backend, PostgreSQL, Redis, or any Chinese production service. The explicit administrator authorization remains auditable and can be disabled separately if required.
