## Context

项目当前已经完成统一 Document Service，用来管理 Resume、JD、Knowledge Base 的上传、OSS 存储、元数据、权限和基础状态。但文档上传后还没有一条正式的后续处理链路，导致“文件已经上传”和“内容已经可供 AI 使用”之间存在空档。随着整体技术架构已经明确采用 FastAPI、PostgreSQL、pgvector、Aliyun OSS 和可替换外部 AI 适配器，当前最自然的下一步就是建立生产级 Document Processing Pipeline。

这条流水线必须满足两个前提：第一，保持现有产品原型交互不变，上传成功立即返回；第二，把处理流程彻底放到后台异步执行，不把解析、chunk、embedding 这些重活塞进上传接口。它还需要与现有 Document Service 保持清晰边界：Document Service 继续管理文档生命周期，Processing Pipeline 负责文档内容理解和向量化结果产出。

## Goals / Non-Goals

**Goals:**

- 建立 Resume、JD、Knowledge Base 共享的一条统一异步文档处理流水线
- 定义 Processing Task 数据模型、状态机、重试规则、日志和配置
- 支持上传完成后自动创建后台处理任务，前台上传接口立即返回
- 使用 MinerU 解析原始文档，统一转换为 Markdown，再做 chunk、embedding 和 pgvector 写入
- 提供处理状态查询和人工重新解析入口
- 为未来新增文档类型预留可扩展的处理注册机制

**Non-Goals:**

- 不实现 Chat Service
- 不实现 RAG 检索编排或召回策略
- 不实现 Prompt 拼接
- 不实现 LLM 问答调用
- 不修改前端原型页面结构和用户交互节奏

## Decisions

### 1. Pipeline 与 Document Service 解耦，通过 Processing Task 衔接

文档上传完成后，Document Service 只负责把文档标记为已上传并创建 Processing Task；后续解析和向量化全部由独立 Pipeline 消费任务完成。

原因：

- 保持上传接口快速返回
- 避免 Document Service 同时承担大文件处理职责
- 后续可替换队列、解析器或 embedding 提供方，而不影响上传契约

备选方案：

- 在上传完成确认接口中直接调用解析流程：实现更直接，但会引入超时、失败耦合和接口不可预测时延

### 2. 采用统一 Processing Task 状态机，而不是把细粒度处理状态混进文档主表

文档主表继续保留面向产品可读的高层状态；更细粒度的处理进度放进 `processing_tasks` 及其阶段字段中，状态流转为：

- `UPLOADED`
- `QUEUED`
- `PARSING`
- `CHUNKING`
- `EMBEDDING`
- `COMPLETED`
- `FAILED`

原因：

- 文档产品状态与处理执行状态分层
- 支持重试、日志和任务级审计
- 不把处理实现细节直接暴露给前端主文档列表

备选方案：

- 只在文档表中维护所有阶段：短期表结构简单，但会让文档元数据和执行状态强耦合

### 3. 后台执行框架先采用应用内异步任务工作器 + 数据库任务表设计

本次 proposal 面向生产级架构，因此处理模型要兼容未来独立 worker，但第一版推荐定义成：

- PostgreSQL `processing_tasks` 任务表作为事实源
- FastAPI 应用或独立 worker 轮询/领取待执行任务
- 任务处理按阶段更新数据库和日志

原因：

- 当前仓库尚未正式引入外部消息队列标准，不宜在 proposal 中强绑 Celery / Kafka / RabbitMQ
- 先统一任务模型和领取协议，后续可在实现阶段选择 worker 部署方式
- 对多文档类型和失败重试更稳定

备选方案：

- 直接绑定 Celery：生态成熟，但会在当前阶段过早绑定运行时栈
- 直接使用 FastAPI BackgroundTasks：实现简单，但不适合生产级重试、恢复和任务查询

### 4. 解析、标准化、chunk、embedding 采用分阶段可替换适配器

流水线分成明确阶段：

1. 文档二进制定位（OSS）
2. MinerU 文档解析
3. Markdown 标准化
4. Chunk Splitter
5. Embedding Service
6. pgvector 持久化
7. 状态回写

每一阶段通过内部 service / adapter 边界隔离，便于后续替换解析器、chunk 策略和 embedding 提供方。

原因：

- 符合项目“外部供应商可替换”的总原则
- 不同文档类型可以共享主流程，但允许在 parser 预处理上有最小差异

备选方案：

- 把整条流水线写成单个超大 service：初期开发快，但很难维护、测试和替换供应商

### 5. 所有文档共享一条 Pipeline，通过文档类型注册差异行为

Resume、JD、Knowledge Base 都走同一任务表、同一状态机和同一处理主流程；差异点只体现在：

- 解析参数
- Markdown 标准化规则
- chunk 策略配置
- 向量命名空间或 metadata 标签

原因：

- 满足“所有文档共享同一 Pipeline”的产品要求
- 后续新增“作品集”或“证书”时只需要注册新的类型规则

备选方案：

- 三类文档分别维护三条处理流水线：会重复实现状态、重试和日志逻辑

### 6. 重试分为自动重试和人工重新解析两层

任务失败后：

- 系统根据可配置的重试上限自动重试可恢复错误
- 超过阈值或遇到不可恢复错误时转为 `FAILED`
- 提供人工重新解析入口，创建新任务或复用原任务版本化重试

原因：

- 网络波动、临时解析错误和 embedding 服务瞬时不可用属于常见可恢复问题
- 人工重试能覆盖文档替换、模型升级或 parser 修复后的重新处理需求

### 7. Pipeline 日志与任务状态分离，日志不写入敏感正文

每个阶段记录结构化日志和任务级事件，但不得在普通日志中写入简历、JD、知识库原文、chunk 正文或 embedding 向量。

记录内容建议包括：

- task_id
- document_id
- document_type
- current_stage
- retry_count
- provider_name
- duration_ms
- error_code

## Risks / Trade-offs

- [Risk] 没有先引入外部消息队列可能限制早期吞吐 → Mitigation: 先统一任务模型与 worker 协议，后续可平滑替换执行器
- [Risk] MinerU 对不同格式和复杂版式结果不稳定 → Mitigation: parser 输出进入 Markdown 标准化阶段，并记录失败原因与人工重试入口
- [Risk] chunk 和 embedding 策略后续会频繁演进 → Mitigation: 将其收敛为独立适配器和配置，不把具体策略硬编码在文档服务层
- [Risk] 文档主状态与任务状态分离后理解成本增加 → Mitigation: 明确“产品状态”和“执行状态”的读写边界，并通过状态查询 API 聚合输出
- [Risk] 异步处理导致上传后短时间不可立即用于问答 → Mitigation: 前端继续展示处理中状态，并通过查询 API 轮询或刷新获取最新结果

## Migration Plan

1. 先在 OpenSpec 中定义统一 Processing Pipeline 能力、状态机和 API 要求
2. 在实现阶段新增 Processing Task 数据模型、阶段状态和日志字段
3. 将统一 Document Service 上传完成事件接入任务创建逻辑
4. 实现后台 worker / executor，按阶段完成解析、Markdown、chunk、embedding 和 pgvector 写入
5. 提供状态查询与人工重试 API
6. 后续再由单独变更把这些结果正式接入 RAG 检索和 AI 问答链路

## Open Questions

- 第一版异步执行器最终采用数据库轮询 worker，还是引入独立队列组件？
- MinerU 的运行方式是独立容器服务、Python 库嵌入，还是外部服务封装？
- Resume、JD、Knowledge Base 的 chunk 策略是否共享默认模板，还是需要从一开始就按类型拆分？
- pgvector 中是按文档类型分 namespace，还是统一表 + metadata 过滤？
