## ADDED Requirements

### Requirement: Persist observed interview concurrency peaks

系统 SHALL 将有效进行中面试数按 5 分钟窗口和 `Asia/Shanghai` 自然日幂等保存最大值。

#### Scenario: Concurrency rises within a bucket
- **WHEN** 同一时间桶后续样本的有效进行中面试数更高
- **THEN** 系统使用更高值覆盖该桶峰值

#### Scenario: Concurrency falls within a bucket
- **WHEN** 同一时间桶后续样本低于已保存峰值
- **THEN** 系统保留原峰值且不得降低

### Requirement: Use real active-session semantics

峰值样本 MUST 只统计状态为 live、未删除且未超过闲置关闭阈值的面试。

#### Scenario: Stale live row remains
- **WHEN** 数据库中存在超过闲置阈值的 live 面试
- **THEN** 该面试不计入并发峰值

### Requirement: Show historical maximum trends

管理平台 SHALL 在运营趋势中展示 7/30/90 天峰值并发面试曲线，区间汇总 MUST 使用最大值聚合。

#### Scenario: Operator selects 30 days
- **WHEN** 管理员查看最近 30 天运营趋势
- **THEN** 每个日期显示该自然日观测到的最高有效并发面试数

#### Scenario: Date predates sampling
- **WHEN** 某日期没有可靠容量样本
- **THEN** 图表显示无覆盖断点，不得显示伪造的零值

### Requirement: Keep peak persistence off the user path

峰值写入失败 MUST NOT 阻断或延迟实时面试用户请求。

#### Scenario: Snapshot storage fails
- **WHEN** 容量任务无法写入峰值
- **THEN** 任务安全降级并等待下一采样周期重试，用户面试继续运行
