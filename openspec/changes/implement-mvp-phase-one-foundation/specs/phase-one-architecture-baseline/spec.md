## ADDED Requirements

### Requirement: Preserve the approved prototype experience while introducing MVP engineering layers
MVP 第一阶段 MUST 保持现有产品原型的页面结构、主要路由、文案层级和核心交互流程不变，并 MUST 只在数据访问、运行配置和工程分层上引入新的实现基础。基础工程改造 MUST NOT 借机重排首页、登录、资料库、计费页、准备页或实时面试页的产品体验。

#### Scenario: Team reviews the first-stage scope
- **WHEN** 团队对照当前原型和第一阶段变更范围进行评审
- **THEN** 变更明确聚焦工程底座、后端框架和通信层，而不包含新的业务流程或页面重设计

### Requirement: Define a stable MVP application and module boundary map
系统 MUST 为 MVP 第一阶段定义稳定的应用分层与模块归属，至少覆盖 `apps/web`、FastAPI 服务端应用、共享协议 / DTO、AI 资产目录和后续桌面伴随程序边界。该边界 MUST 说明哪些职责留在客户端、哪些职责进入服务端，以及哪些模块仅作为后续能力占位而非当前实现逻辑。

#### Scenario: Engineer places a new feature module
- **WHEN** 开发者需要为简历上传或截图回答添加后续实现
- **THEN** 第一阶段架构说明能够指出该代码应该落在哪个应用、共享层或服务端模块中，而不是依赖临时决定

### Requirement: Distinguish foundation work from deferred business logic
第一阶段基础工程 MUST 为上传简历、上传 JD、知识库 / RAG、实时回答、截图回答和会话管理预留清晰模块，但 MUST NOT 实现这些能力的真实业务处理、模型调用、索引构建或持久化规则。所有占位模块 MUST 明确标识为未实现或空实现，而不是伪造真实结果。

#### Scenario: A placeholder module is invoked
- **WHEN** 前端或测试调用第一阶段预留的功能模块
- **THEN** 系统返回一致的未实现占位结果或空实现行为，不伪造业务成功数据
