## ADDED Requirements

### Requirement: Lifecycle-only state uses a lightweight authoritative projection
只需生命周期的高频状态路径 MUST 读取 owner、存在/删除、状态和原超时判断所需时间等必要字段，MUST NOT 为此加载完整配置、对话、使用账单或刷新绑定资料。投影 MUST 保持现有归属、状态转换、错误和响应契约，不缓存终止状态。

#### Scenario: Normal lifecycle status read
- **WHEN** 合法所有者读取 preparing、正常 live 或预警状态且会话绑定多份资料
- **THEN** 返回原字段/值，资料刷新/完整对话读取次数为零，且每次读取取得权威生命周期状态

#### Scenario: Session expires or ends
- **WHEN** 读取发现达到原 idle 边界，或两次请求之间会话已 ended/删除
- **THEN** 维持原终止、计费、资源释放、租约及错误语义，不因投影漏字段而续命或返回过期成功状态

#### Scenario: Foreign or absent session
- **WHEN** 非所有者或合法用户读取不存在/软删除会话
- **THEN** 返回原 403/404 及错误结构，不读取或泄露资料，不改变活动、租约或计费状态

### Requirement: Material reads are deduplicated only within one request
需要完整资料的 list/get/web-state 路径 MUST 保留当前绑定来源、版本、ready、删除、撤销和归属校验；同一次请求对相同 owner 资料可共享一次权威读取，MUST NOT 将复用范围扩展到后续请求、其他 owner 或其他区域。

#### Scenario: Multiple sessions share one owner's materials
- **WHEN** 一次会话列表/聚合状态请求包含多个绑定相同账号资料的会话
- **THEN** 同一 document ID 的资料读取在本次调用内至多执行一次，不同资料仍分别读取，且每个会话保持原归属校验、绑定、可用性、顺序和响应内容

#### Scenario: A bound material changes before the next request
- **WHEN** 首次读取后资料被删除、撤销、改版本或 ready 状态变化，再发起新的完整状态读取
- **THEN** 新请求反映权威资料变化，不复用上次请求旧结果、不静默替换来源，也不绕过回答前的资料校验

#### Scenario: Different owners request state concurrently
- **WHEN** 两个合成账号并发读取各自状态且资料标识相似
- **THEN** 响应和读取复用严格保持 owner 隔离，资料正文与绑定不能跨账号出现

### Requirement: Synchronous state IO does not block the event loop
本轮选定的异步状态路由 MUST 将同步服务/仓库 IO 通过现有受控执行方式完成并等待其结果，保持公开字段、状态码、异常和超时语义。已有独立控制执行器与轻量心跳/ACK/预取路径 MUST 保留其边界，不增加无限后台队列。

#### Scenario: Slow synchronous status dependency
- **WHEN** 测试替身阻塞选定状态路由的同步 IO，且同一事件循环执行独立 sentinel
- **THEN** IO 尚未完成时 sentinel 能推进，IO 完成后路由返回与原实现等价的响应

#### Scenario: State IO raises or request ends
- **WHEN** 同步状态读取产生原业务异常、仓库异常或请求取消
- **THEN** 路由维持相应错误处理，不留下未受控后台任务、不绕过权限，也不影响后续合法读取

#### Scenario: Existing optimized paths are exercised
- **WHEN** 回归执行轻量 web-heartbeat、ACK 兼容/归属、控制面、问题预取及会话清理
- **THEN** 维持既有资料读取次数、缓存归属与过期规则、执行器隔离和资源释放合同
