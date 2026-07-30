## ADDED Requirements

### Requirement: Persist daily operational history
系统 SHALL 按 `Asia/Shanghai` 自然日保存脱敏运营指标快照，日快照 MUST 长期保留，且 SHALL NOT 包含用户标识、资料内容、对话、音频或截图。

#### Scenario: Daily snapshot is generated
- **WHEN** 聚合任务计算一个已结束自然日
- **THEN** 系统按允许的指标目录保存该日聚合值、样本量、覆盖状态、口径版本和计算时间

#### Scenario: Historical daily data remains queryable
- **WHEN** 管理员查询已保存的历史日期
- **THEN** 系统返回该日期快照且不会因原始业务表后续状态变化而静默改写历史值

### Requirement: Aggregate idempotently and independently
系统 SHALL 通过独立于用户请求的幂等任务生成快照，MUST 防止多个实例重复累计，并 SHALL 确保聚合失败不阻断用户端面试、支付或资料处理。

#### Scenario: Same bucket is recomputed
- **WHEN** 调度重试同一粒度、日期和指标
- **THEN** 系统使用唯一键覆盖该快照而不是增加重复记录

#### Scenario: Multiple workers start together
- **WHEN** 多个实例同时尝试执行相同聚合
- **THEN** 系统只允许一个持锁实例执行，其余实例安全退出或等待后重查

### Requirement: Backfill only trustworthy history
系统 SHALL 支持按日期范围回填可由权威持久化数据推导的指标，并 MUST 对无法可靠回填的指标标注覆盖起点或部分覆盖。

#### Scenario: Backfill persisted business events
- **WHEN** 运维人员回填注册、面试、订单、账本或资料任务历史
- **THEN** 系统从权威业务表重建每日快照并记录回填执行结果

#### Scenario: Historical latency events are unavailable
- **WHEN** 某日期缺少完整的 AI 或 ASR 延迟事件
- **THEN** 系统返回缺失或部分覆盖状态，不得将未知值绘制或统计为零

### Requirement: Provide bounded trend queries
系统 SHALL 为具备 `observability.read` 权限的管理员提供 7 天、30 天和 90 天趋势查询，响应 SHALL 包含指标元数据、对齐的数据点、区间汇总、上一等长区间对比、时区和更新时间。

#### Scenario: Administrator requests a 30-day trend
- **WHEN** 已授权管理员查询允许的指标和 `30d` 范围
- **THEN** 系统返回最多 30 个自然日数据点以及当前区间和上一等长区间的汇总比较

#### Scenario: Query exceeds allowed range
- **WHEN** 管理员请求超过 90 天、未知指标或超过指标数量限制
- **THEN** 系统拒绝请求并返回安全、可操作的校验错误

#### Scenario: Unauthorized user requests trends
- **WHEN** 普通用户、无效管理会话或缺少 `observability.read` 权限的管理员请求趋势
- **THEN** 系统拒绝访问且不返回任何运营聚合数据

### Requirement: Keep metric definitions consistent
系统 MUST 使用服务端指标注册表统一定义指标名称、单位、聚合方式、可回填性和说明，管理端 SHALL 使用接口返回的元数据展示单位和口径。

#### Scenario: Dashboard renders a metric
- **WHEN** 趋势接口返回某项指标
- **THEN** 管理端使用同一响应中的名称、单位、覆盖状态和说明展示该指标

#### Scenario: Metric definition changes
- **WHEN** 某项统计口径发生版本化变化
- **THEN** 新快照记录新口径版本，旧快照保持可追溯且不得无说明混合比较

### Requirement: Visualize trends without changing user flows
管理后台 SHALL 在现有运营总览中增加 7/30/90 天筛选、分组趋势曲线、空数据状态、加载失败状态和最后更新时间，并 MUST NOT 修改用户端页面、路由或业务流程。

#### Scenario: Operator opens operations overview
- **WHEN** 管理员进入运营总览
- **THEN** 系统保留现有即时指标卡片，并在其下展示默认 30 天核心趋势

#### Scenario: Trend data has gaps
- **WHEN** 所选指标包含缺失或部分覆盖日期
- **THEN** 图表明确显示数据缺口和覆盖说明，不以连续零值误导管理员

#### Scenario: Trend API is unavailable
- **WHEN** 趋势接口加载失败
- **THEN** 页面显示可重试错误且现有即时总览与其他管理功能仍可使用

### Requirement: Expose aggregation health
系统 SHALL 向授权管理员展示最后成功聚合时间、待补日期数量和最近一次聚合结果，且 SHALL NOT 暴露数据库凭证或敏感原始记录。

#### Scenario: Scheduled aggregation stops
- **WHEN** 最近成功聚合时间超过预期调度窗口
- **THEN** 运营总览显示数据延迟状态和安全的诊断提示
