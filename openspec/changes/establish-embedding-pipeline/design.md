## Context

当前系统已经具备统一 Document Service、Document Processing Pipeline 和独立 Document Parser Service，上传文档可以被统一解析成标准 Markdown，但 Markdown 之后的 Embedding 处理链路仍然停留在基础占位实现。随着后续 RAG 检索、知识召回和问答上下文构建都将依赖稳定的向量数据，当前最自然的下一步就是把 Chunk、Embedding、pgvector 写入和向量重建能力独立成正式的 Embedding Pipeline。

当前这层能力需要满足几个前提：

- 不改变前端原型、上传交互和面试页面
- Resume、JD、Knowledge Base 都走同一条向量化流水线
- Parser 只负责输出标准 Markdown，Embedding Pipeline 只消费 Markdown
- 向量写入必须支持重新构建、批量处理和可替换模型
- 日志、状态和错误处理不能泄露原始正文、chunk 全文或 embedding 数值

## Goals / Non-Goals

**Goals:**

- 建立独立的 Embedding Pipeline，统一负责 Markdown 清洗、切块、元数据构建、向量化和 pgvector 写入
- 定义 Chunk Splitter、Chunk Metadata Builder、Embedding Service、Vector Store 和状态回写边界
- 支持 Resume、JD、Knowledge Base 共享流程，同时允许按类型选择不同 Chunk 策略
- 支持不同 Embedding Model、批量向量化和人工重新构建向量
- 定义 Embedding 阶段状态、失败重试和配置管理约定
- 为后续 Retriever / RAG 提供统一、可查询的向量数据来源

**Non-Goals:**

- 不实现 Retriever
- 不实现 Reranker
- 不实现 Chat Service
- 不实现 Prompt 拼接
- 不修改前端原型结构或交互

## Decisions

### 1. 采用“Parser 输出 Markdown，Embedding Pipeline 消费 Markdown”的边界

Embedding Pipeline 不读取原始二进制文档，也不参与文档解析；它只接收 Parser Service 产出的标准 Markdown 和相关文档元数据。

原因：

- 保持 Parser 与 Embedding 各司其职
- 让 Chunk / Embedding / Vector Store 完全脱离文件格式差异
- 后续如果 Parser 更换实现，不影响向量化主流程

备选方案：

- 让 Embedding Pipeline 直接读取原始文档：会重新引入格式耦合，并重复解析职责

### 2. 采用“Cleaner → Splitter → Metadata Builder → Embedding → Vector Store”的固定处理序列

Embedding Pipeline 的主处理顺序固定为：

1. Markdown Cleaner
2. Chunk Splitter
3. Chunk Metadata Builder
4. Embedding Service
5. pgvector Storage
6. 状态回写

原因：

- 让 Markdown 清洗先于切块，保证 chunk 边界更稳定
- 让 metadata 在 embedding 前就已完整生成，方便批量写入和后续过滤
- 使每一阶段都能独立替换和测试

备选方案：

- Cleaner 与 Splitter 混写在一个服务里：实现快，但会降低策略替换性

### 3. Chunk 策略按文档类型注册，而不是一刀切

Resume、JD、Knowledge Base 共享同一流水线，但允许按文档类型注册不同 Chunk 配置，例如：

- chunk_size
- overlap
- split_priority（标题优先 / 段落优先 / 固定长度）
- metadata 标签模板

原因：

- Resume 通常更适合较短、结构感强的 chunk
- JD 更适合按职责和要求分段
- Knowledge Base 可能更适合较长 chunk 和更高 overlap

备选方案：

- 所有文档共享同一 chunk 参数：实现简单，但会损失召回质量和扩展性

### 4. Embedding Model 通过适配器抽象保持可替换

Embedding Pipeline 只依赖统一 `EmbeddingPort` / `EmbeddingService` 契约，不提前锁定具体模型供应商。适配器需要支持：

- 单条或批量向量化
- provider / model 标识
- retryable 错误分类
- 批量大小限制

原因：

- 当前仓库仍处于 MVP 演进阶段，模型供应商和模型规格很可能迭代
- 批量处理能力是成本和吞吐的关键

备选方案：

- 直接把某个 embedding SDK 写进主流程：开发快，但后续替换成本高

### 5. pgvector 写入采用“统一表 + metadata 过滤”的设计方向

第一版建议采用统一向量表或统一存储接口，由 metadata 区分：

- document_id
- document_kind
- chunk_index
- collection_id（若有）
- parser_version
- embedding_model
- rebuild_version

原因：

- 比“按文档类型拆多表”更便于统一检索和重建管理
- 方便后续做混合知识源过滤
- 更容易在同一生命周期下删除、重建或版本迁移

备选方案：

- 按 Resume / JD / Knowledge 分表：短期隔离清楚，但会增加 schema 和查询复杂度

### 6. 重建向量采用“文档级重建任务 + version 标记”

支持人工或系统触发“重新构建向量”，但不要求用户重新上传文档。推荐做法：

- 基于已有 Markdown 重新发起 Embedding Task
- 为新一轮 chunk / vector 写入记录 `rebuild_version`
- 成功后切换当前活跃版本，旧版本可标记失效或等待清理

原因：

- 支持 chunk 策略变更、模型升级和脏数据修复
- 避免覆盖式更新带来回滚困难

备选方案：

- 直接原地覆盖旧向量：简单，但对回滚和审计不友好

### 7. Embedding 状态只覆盖向量化后半段，不侵入 Parser 状态

处理状态建议细分为：

- `CHUNKING`
- `EMBEDDING`
- `VECTOR_WRITING`
- `COMPLETED`
- `FAILED`

Parser 相关阶段仍归 Parser Service / Processing Pipeline 上半段负责。Embedding Pipeline 只负责自己阶段内的状态推进、失败分类和重试信号。

原因：

- 避免 Parser 和 Embedding 互相覆盖状态
- 让状态查询更容易区分失败发生在哪一段

备选方案：

- 继续只保留一个粗粒度 `EMBEDDING`：实现快，但无法区分 chunk、模型或写库问题

### 8. 结构化日志和批量处理结果都必须避免记录敏感正文

Embedding Pipeline 允许记录：

- task_id
- document_id
- document_kind
- chunk_count
- embedding_model
- batch_size
- duration_ms
- error_code

禁止记录：

- Markdown 全文
- chunk 正文
- embedding 向量数组

原因：

- 符合敏感信息最小暴露原则
- 避免日志成为隐形数据副本

备选方案：

- 记录部分 chunk 预览方便排障：短期方便，但长期会引入隐私风险

## Risks / Trade-offs

- [Risk] 不同文档类型的 chunk 策略设计不合理会影响后续召回质量 → Mitigation: 将 chunk 配置独立化并支持后续重建向量
- [Risk] 批量 embedding 遇到单条失败时会拖慢整批任务 → Mitigation: 设计批量失败拆分与 retryable 分类，不把全部异常视为永久失败
- [Risk] 向量重建会造成旧版本和新版本并存 → Mitigation: 引入 rebuild_version 和 active version 切换规则
- [Risk] pgvector 写入成为瓶颈或失败点 → Mitigation: 通过独立 Vector Store 适配器封装批写、重试和后续扩展
- [Risk] 过早固定模型供应商或表结构 → Mitigation: 抽象 EmbeddingPort 和 VectorStorePort，先固化契约再决定具体实现

## Migration Plan

1. 先在 OpenSpec 中定义 Embedding Pipeline 的能力、状态、重建和配置规则
2. 在实现阶段新增 Cleaner、Splitter、Metadata Builder、Embedding Service 和 Vector Store 边界
3. 将现有 Processing Pipeline 中的 chunk / embedding 占位逻辑替换为独立 Embedding Pipeline 调用
4. 接入 pgvector 写入、批量处理、状态回写和重建入口
5. 后续再通过单独变更接入 Retriever、Reranker 和 RAG 检索编排

## Open Questions

- 第一版 Chunk Splitter 是否需要从开始就支持标题感知和语义分段，还是先以规则分段为主？
- 向量重建时旧版本数据是立即清理，还是保留到后台清扫任务处理？
- pgvector 表中是否需要从第一版开始记录 parser_version / chunk_profile / embedding_model 三类版本信息？
- 批量 embedding 的失败拆分阈值和重试策略是否按模型供应商分别配置？
