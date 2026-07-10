## Context

OfferSteady 当前已经有三类资料入口：Resume、JD、Knowledge Base，并且前端原型已经把这些资料作为面试准备的核心输入。但后端现状仍偏“模块各自上传”，更像是 MVP 上传骨架，而不是统一文档服务。随着生产级基础工程已经补齐统一响应壳、OSS 适配器、PostgreSQL 与运行时配置，当前最合适的下一步不是直接做解析或 RAG，而是先把所有文档的生命周期收敛到一套 Document Service。

这次设计要解决的不是“如何理解文档内容”，而是“如何安全、统一、可审计地管理文档本身”。它需要同时服务 Resume、JD、Knowledge 三类文档，并为后续解析流水线提供稳定的交接入口，但不得让文档服务掺入 Markdown 转换、Chunk、Embedding 或向量检索逻辑。

约束包括：

- 文档包含敏感求职资料，默认最小化保存和严格权限边界
- 文件二进制走阿里云 OSS，对象元数据和权限归属走 PostgreSQL
- 前端页面结构不因后端抽象升级而被重做
- 后续 Processing Pipeline 需要复用文档状态，而不是重新发明一套状态机

## Goals / Non-Goals

**Goals:**

- 建立统一 Document Service，覆盖上传、存储、元数据、状态、列表、删除和权限管理
- 让 Resume、JD、Knowledge 三类文档都通过同一套生命周期接口和数据模型工作
- 使用 OSS 作为文件对象存储，使用 PostgreSQL 作为文档元数据与权限事实源
- 为文件格式、文件大小、唯一命名、删除治理和处理交接建立统一规则
- 为后续 Document Processing Pipeline 预留受控入口和状态交接点

**Non-Goals:**

- 不实现 PDF / DOCX / DOC / TXT / MD 的解析
- 不实现 Markdown 转换、Chunk、Embedding、向量数据库写入或 RAG
- 不实现面试准备阶段的知识抽取、问答生成或资料推荐
- 不把 Document Service 扩展成通用 AI 任务编排器

## Decisions

### 1. Use one Document Service across Resume, JD and Knowledge instead of separate per-module upload flows

统一服务层会把“文档类型”视作元数据字段，而不是让 `resume`、`job-description`、`knowledge` 分别维护三套生命周期。

原因：

- 上传、校验、存储、删除、权限这些规则本质一致
- 以后再新增“项目作品集”“证书”“面试截图资料”等类型时可直接扩展
- 能避免不同模块的状态字段、对象键命名和删除规则逐渐分叉

替代方案是继续保留三套模块级上传实现，只在底层复用 OSS 适配器。这样短期改动少，但长期会把“统一文档管理”又做回三套业务逻辑。

### 2. Use PostgreSQL as the source of truth for document metadata and permissions; OSS stores only object blobs

二进制文件对象放在阿里云 OSS，文档元数据、归属关系、文档类型、状态、删除标记、处理交接状态和审计字段放在 PostgreSQL。

原因：

- 权限控制、列表查询、删除管理和状态流转更适合关系型事实源
- 不能依赖 OSS 对象列表来做产品层面的文档列表与权限判断
- 后续 Processing Pipeline、RAG、计费和审计都需要稳定主键与状态字段

替代方案是把更多状态直接塞进 OSS object metadata。这样能少一张表，但对象元数据难以支撑复杂权限和列表查询，也不适合作为产品事实源。

### 3. Split the lifecycle into upload intent, object upload, completion confirmation, active management, and processing handoff

文档生命周期推荐统一分成：

1. 服务端创建上传意图
2. 客户端直传 OSS
3. 客户端调用完成确认
4. 服务端登记文档元数据并进入文档状态机
5. 后续处理流水线从受控入口拉取或消费该文档

原因：

- 服务端不承担大文件二进制中转，更适合 Web 端与未来桌面端
- “上传成功”与“可用于业务”被明确区分
- 后续处理失败不会污染上传链路，只改变文档处理状态

替代方案是文件先传给 FastAPI 再由后端转存 OSS。这样实现直观，但增加服务端带宽、超时和扩容压力，不适合后续多文档场景。

### 4. Use one canonical document status model that is independent from processing internals

文档服务只维护生命周期状态，例如：

- `pending_upload`
- `uploaded`
- `processing_requested`
- `processing`
- `ready`
- `failed`
- `deleting`
- `deleted`

其中 `processing_requested / processing / ready / failed` 只表达文档是否已完成后续处理，不暴露具体解析实现。

原因：

- 文档服务和 Processing Pipeline 解耦
- 前端只需理解文档是否可用，不需要知道 pipeline 的内部节点
- 后续更换解析实现时，不需要重做文档服务 API

替代方案是把 OCR、Markdown、Chunk、Embedding 等细粒度状态直接塞进文档表。这样前期信息更全，但会把文档服务与处理实现强耦合，违反本次边界。

### 5. Enforce validation at both frontend hint layer and backend authority layer

前端继续显示支持格式和大小说明，但真正的格式校验、大小校验、文档类型限制和权限限制以后端为准。

原因：

- 前端能提供更直接的用户引导
- 后端仍然是唯一可信边界，防止绕过 UI 的非法上传
- 与 OSS 直传结合时，服务端必须先控制上传意图和允许的文件属性

替代方案是仅靠前端校验。这样体验快，但没有安全意义。

### 6. Use soft-delete semantics at the product layer, with asynchronous physical cleanup as a follow-up concern

删除操作在产品层先表现为文档不可见、不可再用于面试和处理，并将状态置为 `deleting/deleted`；OSS 物理删除和外部清理允许异步完成。

原因：

- 用户操作的响应更稳定，不依赖对象存储删除即时完成
- 如果后续处理任务或引用关系存在，可先阻断使用，再做清理
- 审计和恢复窗口更清晰

替代方案是同步强删除数据库记录和 OSS 对象。这样表面简单，但一旦 OSS 删除失败或存在并发处理任务，状态就会不一致。

### 7. Reserve a processing handoff contract instead of embedding pipeline logic in the document service

Document Service 会预留“可请求处理”“待处理查询”“处理结果回写”的边界，但不直接负责解析实现。

推荐边界：

- 文档元数据中记录 `processing_status` / `processing_requested_at`
- 提供内部服务方法或受控接口，供后续 Processing Pipeline 领取待处理文档
- 处理结果通过回写状态进入 `ready` 或 `failed`

原因：

- 能让后续 Processing Pipeline 独立演进
- 文档服务只负责生命周期，不负责内容理解

替代方案是现在就把解析任务、队列、状态明细直接设计进 Document Service。这样会提前把两个 change 混在一起，扩大本次范围。

## Risks / Trade-offs

- [Risk] 统一 Document Service 会要求现有 Resume / JD / Knowledge 上传骨架重构 → Mitigation: 保留文档类型字段和兼容 API 命名，在实现阶段逐步把内部逻辑收敛到统一服务
- [Risk] 直传 OSS 需要前后端配合完成确认，流程比单次上传更长 → Mitigation: 统一上传意图协议和状态提示，前端明确区分“上传完成”和“可用于面试”
- [Risk] 软删除会让数据库和 OSS 在短时间内同时存在对象 → Mitigation: 以数据库状态作为产品真相，并定义异步清理约定
- [Risk] 文档状态如果过粗，后续排查处理问题信息不足 → Mitigation: 生命周期状态保持稳定，同时允许内部处理日志或任务表承载更细粒度信息
- [Risk] 现在先只做文档服务，短期内知识库仍然不能直接用于 RAG → Mitigation: 明确这是有意分层，让后续 Processing Pipeline 可以直接建立在统一文档事实源之上

## Migration Plan

1. 在 OpenSpec 中先定义统一文档生命周期能力及可测试场景。
2. 实现阶段先建立 PostgreSQL 文档元数据模型、Document Service 与统一 API。
3. 把当前 Resume、JD、Knowledge 上传入口改为复用统一 Document Service，而不是各自直接处理。
4. 保留当前支持的文件格式集合，并把文件大小和对象键规则收敛到统一校验器。
5. 后续单独变更再接入 Document Processing Pipeline、解析任务和 RAG 链路。

回滚策略：

- 如果统一服务在实现中引入风险，可保留原有模块级路由外观，但内部回退到旧逻辑
- PostgreSQL 元数据表可通过迁移回滚；OSS 对象命名规则保持前缀隔离，避免影响已有数据

## Open Questions

- 文档大小上限是否三类文档统一，还是 Resume / JD / Knowledge 各自有不同配额？
- 删除后的保留期是否需要产品级回收站，还是 MVP 仅保留软删除不可见状态？
- Processing Pipeline 最终是通过内部任务表、消息队列还是轮询接口对接？
- Knowledge 文档是否需要额外的“所属资料库”关系字段，还是统一文档模型外加可选关联表即可？
