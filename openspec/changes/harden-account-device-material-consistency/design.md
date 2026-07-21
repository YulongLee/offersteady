## Context

当前 Web 登录使用真实短信身份，但 AuthenticationRepository 仍固定为进程内存实现；面试和资料虽已有 PostgreSQL 仓储，Web 聚合状态只返回 5 场会话且首页资料统计为硬编码。桌面端已经把设备身份写入 Electron `userData`，机器码由设备 ID 稳定派生，但缺少明确的不可变和损坏恢复边界。

## Goals / Non-Goals

**Goals:**

- 让手机号身份、认证会话、历史面试和资料元数据在服务重启、退出登录和再次登录后保持一致。
- 让前端显示服务端真实历史和资料统计。
- 让一台桌面设备在普通生命周期内保持同一个机器码。
- 禁止生产环境静默使用内存仓储。

**Non-Goals:**

- 不更换短信、OSS、MinerU、Embedding、Rerank 或模型供应商。
- 不改变现有原型页面结构和创建面试流程。
- 不实现多租户组织、设备共享或账号合并。

## Decisions

### Decision: PostgreSQL is authoritative for commercial account identity

新增 PostgreSQL AuthenticationRepository，复用现有认证表并在有数据库配置时启用。生产环境没有数据库或初始化失败时启动/请求失败，不回退内存。

Alternative: 把手机号到 userId 的映射写入本地文件。该方案不支持多实例、容器重启和并发，因此不采用。

### Decision: Web state returns full user history and the page chooses presentation limits

后端返回当前用户完整会话列表，首页继续在 UI 层截取最近 5 场。这样重新登录不会因聚合接口截断而误认为历史被重置，后续历史页也可复用同一事实源。

Alternative: 新增独立历史分页接口。本轮先保持协议最小变化，数据量增长后再增加分页。

### Decision: Material summary is derived, not stored separately

首页按 `librarySources` 的 kind、status 和 syncStatus 即时计算统计，避免新增容易漂移的计数表。知识材料按 document ID 去重，不重复计算 `knowledgeDocuments` 和 `librarySources`。

### Decision: Device code is derived from a persistent installation identity

继续使用 Electron `userData/device-pairing.json` 中的 deviceId，机器码只由该 ID 派生。普通启动、登录变化、面试绑定和应用升级不写新 ID；仅显式重置或应用数据被用户删除时生成新身份。

## Risks / Trade-offs

- [Risk] 老用户身份此前只存在进程内存，部署后无法自动恢复旧 userId -> 使用手机号哈希重新建立稳定记录；已有错误归属数据需单独迁移，不自动跨用户合并。
- [Risk] 返回完整历史在数据量很大时响应变慢 -> 当前 v0.1 数据量可接受，后续引入游标分页。
- [Risk] 生产依赖失败会让功能直接报错 -> 这是预期的 fail-closed 行为，配合结构化日志定位配置或网络问题。
- [Risk] 6 位机器码存在理论碰撞 -> 服务端仍以 deviceId 校验登记；后续规模扩大时可升级为更长配对码。

## Migration Plan

1. 部署 PostgreSQL AuthenticationRepository 并复用 `0006_sms_authentication_service.sql` 表。
2. 先启动后端确认数据库和 OSS 配置可用，再发布 Web。
3. 用户下一次短信登录时按手机号哈希复用或创建唯一身份。
4. 现有桌面 `device-pairing.json` 原样保留，无需用户重新获取机器码。
5. 回滚时可切回旧应用版本，但生产环境不得删除新认证数据。

## Open Questions

- 历史面试超过当前产品合理上限后，单独增加分页历史页。
- 多设备同账号的设备管理和远程解绑在后续 change 处理。
