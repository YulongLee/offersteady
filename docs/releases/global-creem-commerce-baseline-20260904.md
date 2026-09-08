# Global Creem commerce development baseline

Recorded: 2026-09-04 (Asia/Shanghai)

This read-only baseline precedes OpenSpec change `add-global-creem-commerce`. No service was restarted and no production state was modified while capturing it.

## Global production

- Host: `47.84.65.103`
- Public URL: `https://offersteady.com`
- Current release: `/opt/offersteady-global/releases/20260904-global-complete-1`
- Previous release: `/opt/offersteady-global/releases/20260904-global-workbench-1`
- Global Web image: `sha256:3f82e7eda0b36b0d4949d51c2fb38df00bc59dc56c3c6cf78580683ea9a4df7a`
- Global Backend image: `sha256:022c1e257fd4573f1e9849bfb9005cece76d5fa1f52520e403f83e116fe9ccee`
- Global Admin image: `sha256:a41f6e0baaa995941313dbd2ec7fd37291dfbc510c6e9030ef34dc0ce495a83d`
- Build version: `global-complete-20260904.1`
- Build locale: `en-US`
- Commerce provider: `none`
- Commerce enabled: `false`
- PostgreSQL migration tracker currently contains `0026_knowledge_collection_lifecycle.sql`; other baseline schema is provided by the existing repository initializers.
- Disk at capture: 49 GB total, 15 GB used, 33 GB available.

Global home and health returned HTTP 200. Chinese production `https://www.mianshiwen.cn/` also returned HTTP 200.

## Rollback commands for a future dormant release

The commerce release must record its own image tags before deployment. A safe rollback disables new Global checkout first, then recreates only the independently deployed Global Web, Backend, and Admin from the baseline images. PostgreSQL and Redis volumes remain mounted and additive commerce records are retained.

```bash
docker tag sha256:3f82e7eda0b36b0d4949d51c2fb38df00bc59dc56c3c6cf78580683ea9a4df7a offersteady-global-web:latest
docker tag sha256:022c1e257fd4573f1e9849bfb9005cece76d5fa1f52520e403f83e116fe9ccee offersteady-global-backend:latest
docker tag sha256:a41f6e0baaa995941313dbd2ec7fd37291dfbc510c6e9030ef34dc0ce495a83d offersteady-global-admin:latest
cd /opt/offersteady-global/releases/20260904-global-complete-1
docker compose --project-name offersteady-global --profile admin --env-file .env.global.production -f infra/compose/docker-compose.global.yml up -d --no-build --no-deps --force-recreate web backend admin
curl -fsS https://offersteady.com/healthz
curl -fsS https://www.mianshiwen.cn/
```

Never run `docker compose down`, delete volumes, or restart Chinese services as part of this rollback.
