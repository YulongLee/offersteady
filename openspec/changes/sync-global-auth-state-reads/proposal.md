## Why

用户已明确授权将本轮国服鉴权与状态读取优化同步国际服，自测通过后上线。同步目标是减少高频请求的重复鉴权读写、资料读取和事件循环阻塞，同时保留国际服既有账号、语言和商业规则；国服验收（历史国服参考：`../../../docs/releases/cn-auth-state-local-20261016.md`）中的合成收益不能直接当作国际服真实 P95 改善结论。

## What Changes

- 将已验收的逐请求权威鉴权合并读取、60 秒限频 last-used 和竞争安全 touch/expiry CAS，以最小节点增量迁移到实际 Global Backend 源；不增加正鉴权缓存。
- 同步 idle 五字段投影、会话列表请求内 document ID 去重和八个纯同步状态 GET 的现有线程池执行方式，保持 Global 原请求/响应、错误和资料新鲜度。
- 保留 Global 邮箱/密码/验证/刷新/改密/重置、默认及面试语言、Creem、独立会员/模拟规则、原关闭开关，以及已发布预取、heartbeat/ACK 和全部 Prompt。
- 对实际 Global 候选执行合成安全竞争、真实隔离本地 PostgreSQL/Redis、ASGI sentinel、区域合同与发布回归；从实际镜像构建八文件最小载荷，权威活动门禁通过后只发布 Global Backend，并验收或安全恢复。

本次用户授权包含开发、自测后国际服上线，无需重复确认。非目标：国服或其它组件发布、Web/Windows/macOS 助手升级、模型/Prompt/语言/功能开关/计费变更、客户端上报合并、指标口径调整、连接池、新依赖、数据库迁移、真实面试/供应商调用、生产压测或 Git 提交/推送。测试只用合成数据，不新增用户音频、转录或资料正文保存。

## Capabilities

### New Capabilities

- `global-authoritative-auth-parity`: 保留 Global 账号生命周期与错误合同，同步逐请求权威合并读取和限频竞争安全活动元数据。
- `global-fresh-state-read-parity`: 同步轻量 idle、请求内资料去重和同步状态 IO 分流，保持区域响应/资料隔离及现有性能能力。
- `global-auth-state-protected-release`: 绑定实际 Global 镜像，保护区域商业/语言/Prompt 与非目标节点，合成验证后通过空闲门禁仅发布 Backend，并完成归属安全恢复与验收。

### Modified Capabilities

无。`openspec/specs/` 的既有入口、恢复和资料管理行为保持；本轮迁移内部效率保证，不改用户行为要求。

## Impact

- 运行增量仅限 `ports/authentication.py`、鉴权 service/内存及 PostgreSQL repository、SessionService、session/web/realtime_speech 三个模块的批准节点；不整体覆盖共享研发文件。
- Global 保留七天及以上购买套餐准入、UTC 每日三场、无国服积分和 60 分钟截止的独立规则；历史线上 mock enabled 为 false，本轮必须重新读取并保持该开关，不以隔离自测启用冒充线上开放。
- 实际基线必须由发布时权威读取确认；[上一轮发布](../../../docs/releases/global-question-prefetch-20261016.1.md)的 `b31a810a…` 镜像与 `c2b7caa3…` 容器只是线索，不作为尚未重核的当前事实。
- 国际服发布控制器、合成验证与脱敏记录；国服、Global Web/Admin/worker/数据库/Redis 和助手保持。
