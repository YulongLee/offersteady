# Global Admin simplified 20260906.1

## Deployment

- Host: `47.84.65.103`
- Admin: `https://admin.offersteady.com`
- Release path: `/opt/offersteady-global/releases/20260906-global-admin-simplified-1`
- Active Global interviews before cutover: `0`

Only the Global Admin image and container were rebuilt and recreated. Global Web, Backend, analytics, PostgreSQL, Redis, and all Chinese production services were not changed by this release.

## Scope

The Global Admin navigation now contains only:

- 运营总览
- 服务器监控
- 用户与权益
- 国际商业化
- 资料任务
- 面试会话
- 审计记录
- 管理员

China-only promotion, domestic order/payment, WeChat/Alipay, referral growth, points catalogue, and redemption-code entries are absent from the Global build. The Chinese Admin definition retains its existing module set.

## Verification

- Admin tests: 50 passed.
- Global and Chinese Admin typecheck/build: passed.
- Strict OpenSpec validation: passed.
- Production Admin index: HTTP 200.
- Production Admin JS asset: HTTP 200, 276882 bytes on loopback.
- Global Backend and Chinese production health: passed.
- Global Admin error scan after deployment: zero.

## Rollback

- Previous release: `/opt/offersteady-global/releases/20260906-global-creem-hardening-1`
- Previous image: `offersteady-global-admin:rollback-before-simplify-20260906`

Rollback only the Global Admin container and do not restart Backend, Web, PostgreSQL, Redis, or Chinese services.
