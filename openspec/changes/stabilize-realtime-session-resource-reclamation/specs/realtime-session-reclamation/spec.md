## ADDED Requirements

### Requirement: Lease-based liveness
系统 SHALL 使用适用于会话模式的网页心跳、桌面心跳、音频活动和发布者活动判断实时会话租约，并在租约过期后先进入疑似失活状态再执行回收。

#### Scenario: Active session is preserved
- **WHEN** live 会话持续收到有效网页或桌面心跳，即使暂时没有音频帧
- **THEN** 系统 MUST 保持会话和 ASR 连接，不得自动结束。

#### Scenario: Dead session expires after grace
- **WHEN** live 会话所有适用租约均过期并超过配置的宽限期
- **THEN** 系统 MUST 将会话标记为失活并触发统一清理。

### Requirement: Idempotent resource cleanup
系统 SHALL 提供按 session 加锁且幂等的清理入口，释放 ASR、WebSocket、事件订阅、worker、计时器、音频缓冲和内存索引。

#### Scenario: Explicit end releases resources
- **WHEN** 用户正常结束面试
- **THEN** 系统 MUST 释放该 session 的所有实时资源并记录清理结果。

#### Scenario: Duplicate cleanup is safe
- **WHEN** 断线处理和 watchdog 同时或重复请求清理同一 session
- **THEN** 系统 MUST 不抛出重复关闭错误，且最终资源计数为零。

### Requirement: Background reclamation
系统 SHALL 运行有界的后台 watchdog 定期扫描失活 live 会话，不得依赖后续 API 请求才能完成回收。

#### Scenario: Browser and companion disappear
- **WHEN** 网页和桌面伴随程序同时停止发送心跳
- **THEN** watchdog MUST 在 TTL 与宽限期后回收会话资源，即使没有新的用户请求。

### Requirement: Observability and rollout safety
系统 SHALL 暴露回收原因、回收耗时、释放资源数量、活动连接数和回收前后 RSS，并支持 dry-run/开关控制。

#### Scenario: Reclamation is measurable
- **WHEN** watchdog 或显式结束完成清理
- **THEN** 指标 MUST 能区分触发原因和每类资源释放结果。

#### Scenario: Dry-run does not interrupt users
- **WHEN** 回收开关处于 dry-run
- **THEN** 系统 MUST 记录候选会话但不得关闭活跃连接或结束面试。
