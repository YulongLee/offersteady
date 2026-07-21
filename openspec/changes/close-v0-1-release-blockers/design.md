# Design

## Database extension

新增幂等迁移并在 PostgreSQL 仓储初始化时执行 `CREATE EXTENSION IF NOT EXISTS vector`。生产部署仍先备份数据库，扩展安装失败时拒绝通过发布验收。

## E2E authentication

ScenarioRunner 在注册成功后更新 TestClient 默认 Authorization Header，保证后续所有上传、会话、回答和历史请求都使用同一真实账号。报告只保留运行时发现的问题，不再无条件附加早期原型时代的静态结论。

## Security baseline

Nginx 对静态页面和代理 API 统一返回 HSTS、CSP、nosniff、frame deny 和 referrer policy。CSP 保留本站 API/WebSocket、图片 data/blob 和支付表单所需能力。

## Desktop identity

本地打包与权限重置统一使用 `com.offersteady.companion`。本地仍为 ad-hoc 签名，因此只改善身份一致性，不能替代 Developer ID 和 notarization。

