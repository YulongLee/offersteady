本能力描述 2026-10-16 已完成的本地开发与交付阶段。该阶段的 local-only 约束和未触碰生产的历史事实保持；2026-10-17 用户另行明确授权的 CN Backend 上线阶段由同一变更下 `cn-auth-state-protected-release` 能力约束。

## ADDED Requirements

### Requirement: Local validation measures reduced work and preserved behavior
本轮验证 MUST 使用合成数据覆盖安全矩阵、并发竞争、PostgreSQL 连接/查询/实际写行计数、状态响应合同和事件循环 sentinel，并输出可复现命令、样本量、失败数和环境。合成耗时 MUST 标注其本地限制，不作为真实线上 P95 改善保证。

#### Scenario: Compare before and after under equivalent synthetic traffic
- **WHEN** 使用相同合成账号、会话、资料和并发请求比较原路径与候选
- **THEN** 报告连接/查询/写入/资料枚举次数及 P50/P95/P99、失败数，确认安全与响应等价，清晰区分真实观测和未测量项

#### Scenario: Validate authoritative PostgreSQL races
- **WHEN** 在隔离本地 PostgreSQL 执行触发点可控的 touch、撤销、刷新与改密竞争
- **THEN** 证明不存在复活或安全字段覆盖，测试不连接生产数据库且夹具不含真实用户信息

### Requirement: Candidate protection starts from the actual CN runtime source
本地候选 MUST 以经核对的实际 CN Backend 运行镜像源码为基线施加本轮最小改动，逐项核对全源差异、公开路由/方法、模块、Prompt 和未批准节点。工作区组合代码、旧发布目录或健康版本字符串 MUST NOT 单独充当运行基线。

#### Scenario: Build a local protected candidate
- **WHEN** 已取得并核对实际镜像及源证据并制作本地候选
- **THEN** 只有本轮批准的鉴权/状态节点发生预期变化，既有心跳、ACK、预取、收费和功能路由保持，候选保护结果可审阅

#### Scenario: Runtime source cannot be verified
- **WHEN** 实际运行基线或候选保护无法在本地验证
- **THEN** 报告限制和未完成项，不把工作区单测宣称为已验证的生产镜像候选

### Requirement: Delivery is local and production remains untouched
用户本轮授权仅为本地开发与自测。系统 MUST NOT 部署、重启生产服务、修改生产配置/数据库、生产压测、创建真实面试或提交推送 Git；后续上线操作必须基于用户另行授权和当时权威运行状态。

#### Scenario: Local tests complete
- **WHEN** 本轮实现和本地自测完成
- **THEN** 交付改动、实测结果、限制和待晚上部署说明，保持国服、国际服及其他组件线上运行不变
