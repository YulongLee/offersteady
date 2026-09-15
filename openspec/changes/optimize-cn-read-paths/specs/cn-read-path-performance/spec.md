## ADDED Requirements

### Requirement: Keep user latency attribution accurate

管理后台请求 SHALL 不计入用户请求 P95；用户 API、后台遥测和实时流 SHALL 保持独立统计。

#### Scenario: Admin polling does not inflate user P95
- **WHEN** 管理端持续轮询 dashboard、趋势或支付摘要
- **THEN** 这些请求不会改变 user API P95，只计入 telemetry 分类

### Requirement: Preserve read-path behavior

只读路径优化 SHALL 保持现有响应结构、权限校验和数据新鲜度边界；缓存或去重不可用时必须回退到原始查询。

#### Scenario: Read optimization falls back safely
- **WHEN** 短时缓存未命中或失效
- **THEN** 服务执行原始只读查询并返回相同结构
