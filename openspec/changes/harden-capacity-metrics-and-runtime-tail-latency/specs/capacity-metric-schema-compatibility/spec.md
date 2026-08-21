## ADDED Requirements

### Requirement: Capacity snapshots accept every emitted granularity
数据库快照约束 MUST 接受容量采样器实际写入的 `capacity_5m`，并继续接受运营聚合使用的 `hourly` 和 `daily`。

#### Scenario: Five-minute peak is sampled
- **WHEN** 容量采样器首次写入 `capacity_5m` 峰值
- **THEN** 数据库保存该样本且不得产生粒度约束错误

#### Scenario: Migration is applied again
- **WHEN** 同一数据库迁移因重启或重复部署再次执行
- **THEN** 迁移安全完成且现有快照不丢失

### Requirement: Capacity persistence remains isolated from interviews
容量采样与峰值持久化 MUST 保持旁路运行，其失败不得阻塞健康检查、实时收音、快答或截图回答。

#### Scenario: Snapshot write fails
- **WHEN** 数据库暂时拒绝容量快照写入
- **THEN** 采样器记录安全错误并在下一周期重试，面试请求继续处理

### Requirement: Deployment verifies real peak persistence
发布验证 SHALL 使用合成容量值执行一次实际数据库 upsert，并确认较低的后续样本不会降低已保存峰值。

#### Scenario: Peak rises and falls
- **WHEN** 同一 5 分钟桶依次写入 2、7、4
- **THEN** 最终保存值为 7 且采样计数单调增加
