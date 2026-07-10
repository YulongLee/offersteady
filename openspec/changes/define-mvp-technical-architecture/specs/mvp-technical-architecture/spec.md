## ADDED Requirements

### Requirement: Architecture design MUST define the MVP system boundaries
系统 MUST 为 OfferSteady MVP 提供一份统一技术架构说明，明确浏览器端、桌面伴随程序、应用 API、AI 编排层、资料处理链路、计费系统和数据存储之间的职责边界。该说明 MUST 区分当前原型已存在的模块、MVP 计划实现的模块，以及后续阶段才考虑的扩展模块。

#### Scenario: Team reviews the architecture overview
- **WHEN** 产品、设计和工程成员查看 MVP 架构说明
- **THEN** 文档能够明确说明每个系统组件负责什么、依赖谁、哪些能力不在当前 MVP 范围内

### Requirement: Architecture design MUST describe the core end-to-end workflows
架构说明 MUST 描述至少以下核心链路：资料导入与处理、实时面试辅助、截图问答、跨端会话恢复、积分计费与兑换，以及记录删除或失效处理。每条链路 MUST 说明入口、主要服务、状态归属和关键输出，而不是只罗列组件名称。

#### Scenario: Team traces a user journey
- **WHEN** 团队沿着“上传资料并开始一次面试”的用户路径阅读架构说明
- **THEN** 文档能够指出该路径经过哪些模块、哪些状态在客户端、哪些状态在服务端、哪些事件需要进入 AI 编排或计费系统

### Requirement: Architecture design MUST preserve replaceable provider adapters
架构说明 MUST 要求模型推理、语音转写、文档解析、检索和支付相关集成都经过服务端受控适配器，并 MUST NOT 把供应商 SDK、密钥或供应商专有数据结构直接嵌入客户端核心业务流程。文档 MUST 说明协议层或端口层如何隔离可替换依赖。

#### Scenario: Team evaluates a future provider swap
- **WHEN** 团队需要替换模型、语音或检索供应商
- **THEN** 架构说明能够指出需要替换的适配器边界，而不要求重写 Web、桌面端或核心领域模型

### Requirement: Architecture design MUST define sensitive data handling and deletion boundaries
架构说明 MUST 明确简历、JD、知识材料、截图、转录、兑换码和会话记录等敏感数据的采集入口、默认保存策略、删除入口、权限控制和日志脱敏要求。对于原始音频和 bearer secret，文档 MUST 重申默认不长期保存且不得进入 URL、普通日志或客户端持久化存储。

#### Scenario: Team reviews privacy-sensitive components
- **WHEN** 团队检查音频、资料和兑换相关模块
- **THEN** 架构说明能够说明每类敏感数据在哪里进入系统、在哪里短暂处理、是否持久化以及通过什么入口删除或失效

### Requirement: Architecture design MUST separate real-time interview orchestration from asynchronous processing
架构说明 MUST 把实时面试链路与异步资料处理、截图分析、知识索引、计费记账和运营任务分开建模，并 MUST 说明两类链路的状态同步方式与失败隔离策略。实时回答延迟、终止回答和会话恢复约束 MUST 不依赖异步后台任务先完成。

#### Scenario: Team evaluates a live-session failure mode
- **WHEN** 某个异步资料处理或运营任务失败
- **THEN** 架构说明能够说明实时面试会话如何继续、阻断或降级，而不是要求整个系统停摆

### Requirement: Architecture design MUST identify MVP implementation slices and deferred production hardening
架构说明 MUST 给出面向实现的 MVP 分层与切片顺序，并 MUST 列出刻意延后的生产化事项，例如分布式事务、多实例一致性、KMS、队列基础设施、自动弹性和高级风控。文档 MUST 区分“为了原型简化而暂缓”与“产品行为尚未确认”的两类未决项。

#### Scenario: Team plans the first implementation phase
- **WHEN** 团队基于架构说明拆分后续实现工作
- **THEN** 能够识别哪些模块可以先用简单可替换实现落地，哪些能力必须等产品或安全决策确认后再进入开发
