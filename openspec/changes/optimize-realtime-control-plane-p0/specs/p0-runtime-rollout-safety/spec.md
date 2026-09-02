## ADDED Requirements

### Requirement: Production switch is gated by active realtime usage
生产切换 MUST 在确认没有活跃面试和活跃音频流后执行，除非用户另行明确批准带会话切换。

#### Scenario: Active interview exists
- **WHEN** 发布前检查发现活跃面试或音频流
- **THEN** 系统不得替换生产入口并 SHALL 等待新的安全窗口

### Requirement: Baseline rollback remains immediately available
发布 MUST 记录当前 Git 提交和生产镜像，保留旧容器及旧 Redis 数据，且回滚 MUST 不依赖删除或逆向迁移用户数据。

#### Scenario: Post-release validation fails
- **WHEN** API、绑定、字幕、回答、截图或计费任一核心验收失败
- **THEN** 入口切回基线镜像，旧客户端重新连接后继续使用基线行为

### Requirement: P0 performance and correctness are jointly verified
上线验收 MUST 同时验证长尾性能与业务正确性，不得以降低字幕实时性、文本稳定性或回答能力换取 API 指标。

#### Scenario: Synthetic control-plane load runs
- **WHEN** 10 至 30 台合成设备产生正常心跳和失效绑定重试
- **THEN** 普通 API P95 不高于 500 ms、P99 不高于 1 s、5xx 为零，且稳态不存在全局大快照写入

#### Scenario: Realtime regression suite runs
- **WHEN** 测试执行收音、Partial、Final、重连、快答、截图和积分场景
- **THEN** 字幕不覆盖不回退、回答顺序不变、积分只扣一次，首句和回答耗时不劣于基线
