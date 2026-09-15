# Global app entry shell 2026-09-15

## Release

- Host: `47.84.65.103`
- Public site: `https://offersteady.com`
- Release path: `/opt/offersteady-global/releases/20260915-global-app-entry-shell-1`
- Scope: Global Web entry shell only
- Build manifest version: `global-app-entry-shell-20260915.1`

## Change

The `/app` route now shows a lightweight English loading shell immediately while React restores the workspace. The public SEO homepage remains unchanged. The shell is removed after the first React frame commits.

## Deployment safety

- Pre-cutover gate: zero active Global interviews in the recent 30-minute window.
- Only `offersteady-global-web-1` was rebuilt and recreated.
- Backend, Admin, analytics, material worker, PostgreSQL, and Redis were not recreated.
- Rollback image retained as `offersteady-global-web:rollback-before-app-entry-shell-20260915`.
- Previous release remains available at `/opt/offersteady-global/releases/20260915-global-production-startup-1`.

## Verification

- `https://offersteady.com/healthz` passed.
- `https://offersteady.com/offersteady-global-build.json` reports production, `en-US`, and `global-app-entry-shell-20260915.1`.
- `https://offersteady.com/app` contains the entry shell marker and `Opening your workspace` copy.
- Core container identities and start times were unchanged.
