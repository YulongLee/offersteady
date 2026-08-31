## ADDED Requirements

### Requirement: Streaming connection duration is excluded from ordinary API latency
容量监控 MUST 将实时语音与截图的 `/stream` 请求分类为 SSE 流，并 MUST 从普通 API P95/P99 样本中排除其完整连接持续时间。

#### Scenario: Screenshot SSE stays open
- **WHEN** 截图请求流保持连接数秒后正常结束
- **THEN** 其持续时间计入 SSE 连接时长统计且不进入普通 API P95/P99

#### Scenario: Control API completes slowly
- **WHEN** 非流式控制 API 耗时超过阈值
- **THEN** 其耗时继续进入普通 API P95/P99 和慢请求计数

### Requirement: Request classification remains observable and content-free
监控摘要 SHALL 分别提供普通 API 请求量/延迟与 SSE 连接量/持续时间，且 MUST NOT 记录音频、转录、截图或回答内容。

#### Scenario: Operator reviews release impact
- **WHEN** 运营查看发布后的容量摘要
- **THEN** 可以独立比较控制 API 请求率与 SSE 连接持续时间，数据只包含路由类别、计数和耗时
