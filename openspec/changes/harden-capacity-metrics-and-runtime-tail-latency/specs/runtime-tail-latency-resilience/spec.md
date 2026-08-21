## ADDED Requirements

### Requirement: Incremental event waits avoid full-stream amplification
生产 Redis 事件仓库 SHALL 使用有界游标索引或等价机制读取游标后的增量事件，空闲等待和正常唤醒不得在每次循环中解析完整保留 Stream。

#### Scenario: Long stream remains idle
- **WHEN** Stream 已保留大量历史事件且消费者等待新事件
- **THEN** 系统执行一次有界阻塞等待，不重复全量扫描和反序列化全部历史事件

#### Scenario: New event wakes consumer
- **WHEN** 新事件在阻塞期限内写入
- **THEN** 消费者只收到游标后的单调增量并及时返回

### Requirement: Existing event cursors remain recoverable across deployment
优化后的仓库 MUST 兼容升级前已经存在但没有快速索引的 Redis Stream，并保留游标过期时的 snapshot 恢复语义。

#### Scenario: Legacy stream has no cursor index
- **WHEN** 客户端使用升级前的有效 cursor 重连
- **THEN** 系统通过兼容路径返回 cursor 后事件且不得要求用户重新开始面试

#### Scenario: Cursor predates retained stream
- **WHEN** 客户端 cursor 已早于最小保留 cursor
- **THEN** 系统标记增量不可恢复并返回当前 snapshot 恢复信号

### Requirement: Blocking event reads use isolated bounded resources
长时间 Redis 阻塞读取 MUST 与普通 API、授权校验、容量采样及短时快照读取使用的通用执行资源隔离，并设置有界 worker 数和等待期限。

#### Scenario: Many SSE clients are idle
- **WHEN** 多个网页和桌面 SSE 同时等待且没有新事件
- **THEN** 健康检查和普通 API 仍能及时执行，不因默认线程池耗尽而排队到阻塞等待之后

### Requirement: Session updates refresh only affected snapshots
初始 SSE snapshot SHALL 保持完整；后续事件更新 SHALL 只刷新与事件类型相关的转写或问题候选数据，并不得为增量 payload 重读完整历史事件。

#### Scenario: Screenshot progress arrives
- **WHEN** 会话收到截图进度事件
- **THEN** 路由发送该增量事件且不重新读取完整转写、候选和历史事件列表

#### Scenario: Transcript arrives
- **WHEN** 会话收到 `transcript-updated`
- **THEN** 路由刷新转写快照并保持候选与其他状态单调不回退

### Requirement: Tail-latency regression is measurable
回归验证 MUST 同时报告并限制健康检查与事件唤醒的 P95/P99，并验证长事件流下 Redis 全量扫描次数不会随空闲等待次数线性增长。

#### Scenario: Synthetic concurrency test runs
- **WHEN** 测试并发运行空闲 SSE、事件发布和健康请求
- **THEN** 报告包含样本量、P50/P95/P99、失败数和 Redis 命令计数，且不包含用户内容
