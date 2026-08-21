## Why

线上容量采样持续尝试写入数据库未允许的 `capacity_5m` 粒度，导致峰值监控失效并每 30 秒产生错误；同时实时会话事件流会反复全量扫描 Redis Stream，并把阻塞等待放入通用线程池，在活跃连接和历史事件增长时可能造成 CPU 饱和与接口分钟级长尾。两项问题都发生在生产旁路或实时基础设施中，需要在不改变用户操作和回答逻辑的前提下修复。

## What Changes

- 增加向前兼容数据库迁移，使容量快照明确支持 `capacity_5m`、`hourly` 和 `daily`，并保证重复执行安全。
- 为容量峰值持久化增加真实约束回归测试与可观测错误，避免监控静默失效或干扰面试请求。
- 优化 Redis 会话事件游标查找，避免每次阻塞等待前后反复解析完整事件流，同时兼容升级前已有 Stream 数据。
- 将长时间 Redis 阻塞读取隔离到专用有界执行器，避免占满通用异步线程池。
- 让会话 SSE 只在相关事件发生时刷新转写/候选快照，避免无关截图、设备和性能事件触发全量读取。
- 增加并发 SSE、长事件流、健康检查和容量采样的合成负载回归，记录优化前后 P50/P95/P99 与 Redis 命令量。
- 不改变收音、问题确认、快答、截图回答、计费、页面文案或客户端协议。

## Capabilities

### New Capabilities

- `capacity-metric-schema-compatibility`: 容量峰值采样的数据库粒度、迁移兼容、失败隔离和验证要求。
- `runtime-tail-latency-resilience`: 实时事件读取的有界资源隔离、增量读取、兼容恢复和长尾性能门槛。

### Modified Capabilities

无。

## Impact

- Backend：PostgreSQL migration、管理端容量仓库、Redis realtime repository、会话/桌面 SSE 路由与运行配置。
- Tests：数据库迁移回归、Redis 命令量、并发 SSE、健康检查和事件恢复测试。
- Infrastructure：复用现有 PostgreSQL 与 Redis，不引入新服务；部署仅需重建后端并执行幂等迁移。
- Privacy：只处理指标数值、游标和事件元数据，不新增音频、截图、问题或答案正文持久化。
