## ADDED Requirements

### Requirement: Realtime delivery metrics exclude user content
系统 SHALL 记录会话 SSE 的连接建立、首 snapshot、连接时长、关闭原因、重连次数和 fallback snapshot 次数，并 MUST NOT 在性能遥测中记录音频、截图、问题、回答、简历、JD 或知识资料正文。

#### Scenario: Stream connects and later closes
- **WHEN** 会话流成功交付首 snapshot 后因网络关闭
- **THEN** 遥测包含建连耗时、首 snapshot 耗时、连接时长和安全原因枚举，但不包含会话内容

### Requirement: Latency is reported by request class
容量监控 SHALL 分别报告普通控制 API、恢复 snapshot 与 SSE 握手的请求量和尾延迟，并继续提供兼容的总体 API P95。

#### Scenario: Long-lived SSE and control requests coexist
- **WHEN** 统计窗口内同时存在 SSE 建连、恢复 snapshot 和普通控制 API
- **THEN** 管理端或指标接口可区分三类样本，不用单一总体 P95 推断具体瓶颈

### Requirement: Performance acceptance uses synthetic content
发布前性能回归 MUST 使用合成或脱敏会话，至少覆盖 1、5、10 个活动会话以及断线恢复，并报告请求率、P95/P99、CPU、重连、fallback 和错误数。

#### Scenario: Ten-session load test completes
- **WHEN** 合成负载运行十个活动会话并注入可控断线
- **THEN** 报告包含各请求分类和恢复指标，且测试夹具不含真实用户数据
