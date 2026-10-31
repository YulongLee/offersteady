## ADDED Requirements

### Requirement: Prove reduced work and preserved behavior locally
验收 MUST 用合成数据运行身份/取消/刷新、资料生命周期、既有面试与收费相关回归，记录网络/资料/连接/查询计数及实际结果，MUST 区分本地证据与线上收益。

#### Scenario: Compare baseline and candidate
- **WHEN** 对同一合成并发波次及多会话资料集测试前后实现
- **THEN** 状态语义等价且重复工作下降，记录样本、错误和资源计数，不以减少功能制造降幅

#### Scenario: Evaluate connection reuse
- **WHEN** 本地比较短连接与有界复用
- **THEN** 仅使用隔离localhost合成数据库，比较同SQL/并发、建连次数、p50/p95、错误和资源归还，并保持产品运行时/依赖/配置不变

### Requirement: Keep this delivery local and protect the deployed baseline
本轮 MUST NOT 部署/重启线上、修改生产或真实用户数据、调用真实模型、压测或执行Git提交推送。必须保护已有普通/模拟面试、简历优化、多屏、支付、模型、助手及SEO增量。

#### Scenario: Local validation completes
- **WHEN** 实现、自测和严格规范校验通过
- **THEN** 交付精确改动、验证结果、限制及待晚间发布说明，不执行线上切换

#### Scenario: Baseline differs from a full source build
- **WHEN** 本地源构建不能证明与线上Web静态包等价
- **THEN** 明确不能直接整体发布，晚间必须从当时实际镜像核对并制作最小增量，保护所有既有功能
