## ADDED Requirements

### Requirement: Background idle session reclamation
系统 SHALL 在应用运行期间按配置间隔扫描并幂等终止超过业务空闲 TTL 的 live 面试，会话终止必须复用统一实时资源清理流程。

#### Scenario: Idle live session is reclaimed without a follow-up request
- **WHEN** live 面试超过 `interview_idle_timeout_seconds` 且后台回收周期到达
- **THEN** 系统将会话标记为 ended，并关闭 ASR provider sessions、发布器、计费线程、队列和会话级短期状态

#### Scenario: Active session is not interrupted
- **WHEN** live 面试在空闲 TTL 内持续发送有效心跳或音频
- **THEN** 后台回收器不终止该会话或其 ASR 连接

#### Scenario: Reclamation is idempotent
- **WHEN** 后台回收与用户结束请求同时或重复处理同一会话
- **THEN** 会话最终为 ended，active provider sessions 为零，且不抛出重复清理错误

### Requirement: Reaper lifecycle and observability
系统 SHALL 在应用关闭时停止后台回收任务，并提供回收运行次数、成功终止数、失败数和最近运行时间等不含敏感内容的指标。

#### Scenario: Application shutdown
- **WHEN** FastAPI 应用进入 shutdown 生命周期
- **THEN** 回收任务被取消并等待退出，实时服务关闭剩余 provider sessions 和线程池

#### Scenario: Reaper failure is isolated
- **WHEN** 某次数据库扫描或单个会话终止失败
- **THEN** 系统记录失败计数并继续服务请求，后续回收周期仍会运行
