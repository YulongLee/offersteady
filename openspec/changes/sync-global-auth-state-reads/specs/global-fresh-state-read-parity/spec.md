## ADDED Requirements

### Requirement: Global idle state uses authoritative lifecycle projection
idle 状态读取 MUST 复用必要五字段权威投影，不加载完整资料/对话/账单，不缓存 owner/ended；MUST 保持原归属/删除、时间边界、错误及调用方结束/计费/资源清理语义。

#### Scenario: Normal and expired states preserve their contracts
- **WHEN** 合法用户读取 preparing/live/warning/expired/ended 的合成会话
- **THEN** 响应字段和值与原实现等价，普通投影资料读取为零，expired 调用方沿用原收尾及失败处理

#### Scenario: Another owner or deleted session is requested
- **WHEN** 用户读取他人、不存在或已删除会话
- **THEN** 返回原 403/404 结构，无资料读取和活动/租约/计费副作用

### Requirement: Global material reuse is limited to the current list request
会话列表 MUST 仅用调用局部 document ID memo 去重相同资料（包括 None）；完整读取 MUST 保持 ready/删除/撤销/版本/索引及 owner 合同，mock 资料版本路径保持，MUST NOT 增加跨请求/owner/区域缓存。

#### Scenario: Shared materials and absent sources appear in multiple sessions
- **WHEN** 一次列表包含多个引用相同有效或缺失资料的会话
- **THEN** 同 document ID 至多读取一次，各会话绑定、顺序、可用性及 mock 版本保持原合同

#### Scenario: Material changes or another owner reads later
- **WHEN** 下一次请求前资料状态/版本变化，或另一 owner 并发发起自己的读取
- **THEN** 每次调用重新读取各自权威资料，变化即时反映且没有前次或他人资料混入

### Requirement: Global synchronous state IO is offloaded without regional body changes
选定八个纯同步状态 GET MUST 由现有 FastAPI/AnyIO 线程池执行；除 `async def` 改 `def` 外签名/装饰器/正文保持实际 Global 版本，MUST 保留网页 Global billing/语言字段、既有控制执行器、预取、heartbeat/ACK 和资源清理边界。

#### Scenario: Slow state dependency does not freeze the event loop
- **WHEN** 真实 ASGI 路由中的同步状态替身阻塞，同时请求独立 loop sentinel
- **THEN** IO 未完成时 sentinel 可推进，原业务错误/取消处理和后续合法请求恢复符合合同

#### Scenario: Regional response and existing optimizations are regressed
- **WHEN** 回归 Global web/state、设备/runtime、会话/复盘、heartbeat/ACK、预取及清理
- **THEN** 原字段、语言、权益与安全错误保持，节点保护证明未替换为 CN 正文或改动控制/预取边界
