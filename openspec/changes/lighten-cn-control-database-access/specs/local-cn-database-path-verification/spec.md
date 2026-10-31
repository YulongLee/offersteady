## ADDED Requirements

### Requirement: Compare actual local control and repository paths
验收 MUST 使用隔离localhost合成PostgreSQL和相同业务数据对照，记录投影字段、资料/SQL/写入/连接次数、池边界、错误和可得耗时分项。MUST 区分建连/借用、查询及整体操作，不能把本地P95当线上承诺。

#### Scenario: Control path comparison
- **WHEN** 相同多资料绑定状态用完整与轻量算法读取
- **THEN** 响应等价，候选无资料查询和附带写入，资源计数及实际样本可复核

#### Scenario: Actual pooled repository comparison
- **WHEN** 相同auth/session业务分别通过原短连接和候选池执行
- **THEN** 结果、事务和身份语义等价，记录建连减少、借用等待和失败数，而非仅测select 1

### Requirement: Preserve today's candidate and keep this delivery local
本轮 MUST 保留今日已完成的状态在途合并/请求内资料复用，以及普通/模拟面试、简历、多屏、收费、模型和SEO。MUST NOT 部署、重启或修改生产、真实用户、供应商、国际服、worker及Git提交/推送。

#### Scenario: Local validation is complete
- **WHEN** 专项/相关回归、独立审查及规范校验完成
- **THEN** 交付本地候选、实测限制和晚间发布待核对项，不执行线上切换

#### Scenario: Diagnostics report timings
- **WHEN** 记录分项、资源和错误结果
- **THEN** 仅输出固定组件/操作标签与脱敏数字，不输出DSN、凭据、SQL参数、用户ID或资料正文
