# Global complete experience release 20260904.1

Deployed: 2026-09-04 (Asia/Shanghai)

## Release

- Public URL: `https://offersteady.com`
- Release version: `global-complete-20260904.1`
- Release path: `/opt/offersteady-global/releases/20260904-global-complete-1`
- Compose project: `offersteady-global`
- Global Web image: `sha256:3f82e7eda0b36b0d4949d51c2fb38df00bc59dc56c3c6cf78580683ea9a4df7a`
- Commerce provider: `none`
- Commerce enabled: `false`

Only the Global Web container was recreated. Global Backend, Admin, analytics, PostgreSQL, and Redis were not restarted. No Chinese production service was changed or restarted.

## Verification

- Global home, login, workbench, materials, billing, guide, legacy invite, build manifest, health, and public state routes returned HTTP 200.
- Every JavaScript and CSS asset referenced by the public home document returned HTTP 200.
- The public home document contained no Han product copy.
- The production manifest reported `en-US`, `commerceEnabled=false`, and `commerceProvider=none`.
- `https://www.mianshiwen.cn/` returned HTTP 200 after deployment.

## Rollback

- Previous release: `/opt/offersteady-global/releases/20260904-global-workbench-1`
- Rollback image tag: `offersteady-global-web:pre-global-complete-20260904.1`
- Rollback image: `sha256:32737e163a1da662dc543d01ec6762e3e98bc4ff242b12771e7dcda469aecf74`

Rollback recreates only the Global Web service from the previous release. Do not stop the Compose project, delete volumes, or restart Chinese services.
