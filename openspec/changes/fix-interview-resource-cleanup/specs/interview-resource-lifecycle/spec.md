## ADDED Requirements

### Requirement: Interview termination releases realtime resources
系统 SHALL 在用户结束面试、管理员终止面试、会话被替换或空闲超时后，关闭该会话的 ASR provider sessions、发布器和桌面绑定，并清空会话级音频队列、临时状态和索引。

#### Scenario: Explicit interview end
- **WHEN** 用户调用面试结束接口
- **THEN** 会话被标记为 ended，所有该会话的 ASR sessions、publishers、bindings 和 in-memory realtime indexes 被释放

#### Scenario: Idle interview reclamation
- **WHEN** heartbeat 超时触发自动回收
- **THEN** 系统执行与显式结束相同的资源清理，且重复回收不会抛出错误

### Requirement: Session-scoped indexes do not accumulate
实时服务 SHALL 在会话终止后移除所有以 session id 或 session/source key 为键的短期缓存、计数器和终止标记；进程级累计指标可保留但不得保存会话对象或 payload。

#### Scenario: Repeated ended sessions
- **WHEN** 连续创建并结束多场面试
- **THEN** 短期会话索引的条目数量不会随历史面试数量无限增长

### Requirement: Expired screenshot uploads are reclaimed
系统 SHALL 按上传意图的过期时间回收未确认意图、待确认 payload 和已上传图片 bytes，并在显式释放、过期清理和重复调用时保持幂等。

#### Scenario: Abandoned upload intent
- **WHEN** 用户上传截图后未确认且超过 TTL
- **THEN** 对应 intent 与 payload 从内存索引中删除，不再占用进程内存

#### Scenario: Completed screenshot task
- **WHEN** 截图回答任务完成或失败
- **THEN** 任务使用的图片 bytes 被释放，重复释放不会报错

### Requirement: ASR closure is observable and idempotent
ASR 网关 SHALL 支持按会话关闭全部 source sessions，重复关闭不创建新连接，并提供 active provider session 数量与关闭失败计数用于诊断。

#### Scenario: Close an already closed session
- **WHEN** 同一会话被显式结束和超时回收路径重复处理
- **THEN** 网关保持 active provider sessions 为零且接口成功返回
