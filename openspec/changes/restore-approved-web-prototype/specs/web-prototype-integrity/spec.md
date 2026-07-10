## ADDED Requirements

### Requirement: The approved web prototype MUST remain stable during backend integration
系统在推进后端联调、服务抽象或基础工程升级时，MUST 保持已批准的 Web 原型页面结构、文案表达和交互顺序稳定。工程实现 MAY 变更适配层，但 MUST NOT 默认改变用户已经确认的原型体验。

#### Scenario: Backend service contract changes
- **WHEN** 后端新增或调整接口、状态字段或统一服务边界
- **THEN** 前端应优先通过兼容适配层消化变化，而不是直接改变已批准页面表现

#### Scenario: Prototype page has been user-approved
- **WHEN** 某个原型页面已经被用户确认
- **THEN** 后续实现型改动不得在未单独提出产品变更的情况下修改其交互和文案

### Requirement: Prototype-facing files MUST be restored when backend implementation accidentally changes product behavior
如果后端实现或联调工作误改了用户可感知的原型层表现，系统 MUST 优先恢复原型层文件到已批准状态。恢复范围 SHOULD 先聚焦于资料页、上传适配层和其他直接影响原型展示的文件。

#### Scenario: Material library prototype is altered by implementation work
- **WHEN** 资料页的布局、提示文案或原型交互因工程实现被意外改变
- **THEN** 系统优先回退这些原型层文件，而不是要求用户接受新的页面表现

#### Scenario: Minimal compatibility is still required for compilation
- **WHEN** 回退原型层后，某些底层协议字段仍是前端编译所必需
- **THEN** 系统只保留最小兼容字段，不把新的服务端行为直接带入原型页面

### Requirement: Backend capability evolution MUST be isolated from prototype behavior by adapters
后端能力可以继续演进，但前端原型 MUST 通过 adapter 或兼容层隔离这些变化。页面组件 SHALL NOT 直接承担“为了匹配新后端 contract 而改原型表现”的责任。

#### Scenario: Document service continues evolving
- **WHEN** 统一 Document Service 继续新增列表、删除或状态管理能力
- **THEN** 这些能力的接入应先落在 adapter 层，且不自动改变原型模式下的页面行为

#### Scenario: Prototype and API modes coexist
- **WHEN** Web 应用同时支持 prototype/fixture 和 api 两种模式
- **THEN** 两种模式都应保持一致的页面表现，而不是因为 API 模式联调导致原型模式展示发生漂移
