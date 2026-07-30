## ADDED Requirements

### Requirement: Report real active interviews
管理后台 SHALL 使用未删除、会话状态、权威业务活动时间和实时连接状态组合判断真实活跃面试，MUST NOT 将软删除或超过空闲阈值的会话计入“进行中面试”。

#### Scenario: Soft-deleted live row exists
- **WHEN** 历史记录仍为 `live` 但 `deleted_at_ms` 已设置
- **THEN** 后台总览和进行中列表均不统计该记录

#### Scenario: Live row has recent activity
- **WHEN** 未删除 `live` 会话在 20 分钟内存在权威业务活动和近期实时连接
- **THEN** 后台将其标记为“真实活跃”

#### Scenario: Live row is stale
- **WHEN** 未删除 `live` 会话超过 20 分钟没有有效业务活动且没有处理中任务
- **THEN** 后台将其标记为“空闲待关闭”而不是“真实活跃”

### Requirement: Keep dashboard and list consistent
管理后台总览的进行中数量和会话列表的活跃分类 SHALL 复用相同查询口径，并 SHALL 返回最后活动时间、空闲时长和安全状态字段。

#### Scenario: Operator opens dashboard and sessions
- **WHEN** 管理员先查看总览再打开面试会话列表
- **THEN** 总览活跃数量等于列表按“真实活跃”分类的总数

### Requirement: Reconcile historical stale sessions
系统 SHALL 提供幂等运维过程，将上线前已超过阈值且无实时连接或处理中任务的 `live` 会话归档为 `ended`，并 MUST 保留历史数据和审计证据。

#### Scenario: Reconciliation is rerun
- **WHEN** 同一批陈旧会话清理任务被重复执行
- **THEN** 已结束会话保持不变，不重复释放资源或生成冲突记录
