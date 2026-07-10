# Migrations Placeholder

未来数据库 schema 变更统一通过这里管理。

当前约定：

- 迁移工具优先使用 Alembic；
- `versions/` 保存按时间顺序追加的迁移脚本；
- 启用 pgvector 的基础初始化放在 `infra/postgres/init/`，业务表结构迁移不要散落到应用代码里；
- 任何 schema 变更都需要对应 OpenSpec 变更、回滚说明和验证步骤。
