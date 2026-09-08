# Global complete-experience rollback baseline

Recorded: 2026-09-04 (Asia/Shanghai)

This is the read-only production baseline for OpenSpec change `complete-global-english-product-experience`.

## Active release

- Host: `47.84.65.103`
- Public URL: `https://offersteady.com`
- Release path: `/opt/offersteady-global/releases/20260904-global-workbench-1`
- Compose project: `offersteady-global`
- Active Global Web image: `sha256:32737e163a1da662dc543d01ec6762e3e98bc4ff242b12771e7dcda469aecf74`
- Previous tagged Global Web image: `offersteady-global-web:global-email-auth-20260904.1` (`sha256:76cb928ba199070664e3c09fd1fc3e7daac5e74c25896f980155ce20e94a8a8d`)

At capture time all six Global containers were running, Global Backend/PostgreSQL/Redis were healthy, `https://offersteady.com/` and `https://offersteady.com/healthz` returned HTTP 200, and `https://www.mianshiwen.cn/` returned HTTP 200.

## Rollback procedure

Rollback is a release operation and MUST NOT be run during local implementation. On the Global host, retag the recorded previous image as `offersteady-global-web:latest`, recreate only the `web` service from the recorded release compose file, then verify Global and Chinese health endpoints. Do not run `docker compose down`, delete volumes, or restart Chinese services.

```bash
docker tag offersteady-global-web:global-email-auth-20260904.1 offersteady-global-web:latest
cd /opt/offersteady-global/releases/20260904-global-workbench-1/infra/compose
docker compose --env-file /opt/offersteady-global/shared/.env.global -p offersteady-global up -d --no-deps --force-recreate web
curl -fsS https://offersteady.com/healthz
curl -fsS https://www.mianshiwen.cn/
```

