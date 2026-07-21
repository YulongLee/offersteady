# Close v0.1 Release Blockers

## Why

全面上线验收发现生产 pgvector 未启用、E2E 工具未携带生产 Token、ASR 验收依赖缺失、Web 存在高危依赖告警和安全响应头缺失，桌面诊断还会把 0 帧结果误判为通过。这些问题会削弱发布证据或直接形成安全风险。

## What Changes

- 为已有及新建 PostgreSQL 数据卷自动启用 pgvector。
- 让 E2E 注册后的所有请求继承 Access Token，并移除已经过时的静态阻断结论。
- 将实时 ASR 验证所需客户端加入生产依赖。
- 升级存在高危公告的 React Router 依赖。
- 为 Web 与 API 响应增加 HSTS、CSP 和常用安全响应头。
- 让桌面诊断将原生探测 `ok=false` 判定为失败。
- 统一本地打包和权限重置使用稳定 Bundle ID。

## Non-goals

- 不伪造 Apple Developer ID、notarization、真实短信和真实支付验收。
- 不在本批次将 JSONB 向量检索改写为 pgvector SQL 索引。
- 不改变产品页面原型或收费规则。

## Capabilities

- `v0-1-release-readiness`: 可重复执行且安全基线明确的 v0.1 发布验收。

