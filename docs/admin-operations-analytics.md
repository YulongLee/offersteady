# 管理后台运营趋势

运营趋势使用脱敏聚合快照，不保存手机号、用户 ID、资料、对话、音频或截图。日快照永久保留，小时快照保留 180 天。

## 手工回填

```bash
docker compose --env-file .env.production \
  -f infra/compose/docker-compose.foundation.yml \
  run --rm analytics sh -lc \
  'cd /app/apps/backend && python -m app.services.admin_analytics_job --all-history'
```

指定日期：

```bash
cd /app/apps/backend
python -m app.services.admin_analytics_job --start-date 2026-07-01 --end-date 2026-07-31
```

命令通过 PostgreSQL advisory lock 和唯一键 upsert 保证重复执行安全。过去未持久化的 ASR 延迟会显示为无覆盖，不会写成零。

## 调度与健康

Compose 中的 `analytics` 服务每小时执行一次小时聚合、前一自然日日聚合和缺口补算。后台通过 `/api/v1/admin/analytics/health` 显示最近聚合状态。

回滚时停止 `analytics` 服务并隐藏管理端趋势区域即可，快照表可以保留，用户端不依赖该能力。
