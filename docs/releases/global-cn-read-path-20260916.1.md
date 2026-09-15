# 国际服只读链路优化

## 范围

- 更新 Global Backend：后台请求归类为 telemetry，不再抬高用户 API P95；增加 live、未删除、最近活动面试查询的部分索引。
- 更新 Global Admin：同步请求分类与 P95 分项监控展示。
- Global Web、PostgreSQL、Redis、分析任务和素材 worker 未重启。

## 验证

- 后端相关测试：24 passed，16 subtests passed。
- 管理端测试：54 passed，typecheck 和生产构建通过。
- 国际服公网 `/healthz` 返回正常，生产环境和 Global 版本标识正确。
- `idx_interview_sessions_live_activity` 已在 Global PostgreSQL 中创建。
- 部署前进行中面试数为 0；部署后无新增后端错误日志。

## 发布与回滚

- 发布目录：`/opt/offersteady-global/releases/20260916-global-cn-read-path-1`
- 当前目录：`/opt/offersteady-global/current`
- Backend 版本：`global-cn-read-path-20260916.1`
- 回滚镜像：`offersteady-global-backend:rollback-before-cn-read-path-20260916`、`offersteady-global-admin:rollback-before-cn-read-path-20260916`
- Global Web 保留原版本：`global-app-entry-shell-20260915.1`。
