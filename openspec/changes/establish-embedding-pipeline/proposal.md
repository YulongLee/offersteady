## Why

当前系统已经建立统一 Document Service、Document Processing Pipeline 和独立 Document Parser Service，文档可以被转换成标准 Markdown，但从 Markdown 到可检索向量数据的后半段能力仍缺失。现在需要把 Chunk、Embedding 和 pgvector 写入正式独立出来，形成一条统一、可重建、可配置的 Embedding Pipeline，为后续 RAG 检索提供稳定数据来源。

## What Changes

- 新增独立的 Embedding Pipeline，统一负责 Resume、JD、Knowledge Base Markdown 文档的清洗、切块、元数据构建、向量化和 pgvector 写入。
- 明确 Embedding Pipeline 与 Document Parser 解耦：Parser 只产出标准 Markdown，Embedding Pipeline 只消费 Markdown 并完成 Chunk / Embedding / Vector Storage。
- 定义统一 Chunk Splitter、Chunk Metadata Builder、Embedding Service、pgvector Storage 和 Embedding Task 边界。
- 增加 Embedding 阶段状态、批量处理、失败重试、重新构建向量和 Chunk 配置管理能力。
- 支持按文档类型选择不同 Chunk 策略和不同 Embedding Model，但不改变前端原型交互。
- 本次只覆盖向量化数据生产链路，不实现 Retriever、Reranker、Chat Service 或 Prompt 拼接。

## Capabilities

### New Capabilities
- `embedding-pipeline`: 定义统一 Markdown 清洗、切块、向量化、pgvector 写入、状态管理与重建机制

### Modified Capabilities
- None

## Impact

- Affected backend: `apps/backend` 的文档处理服务、chunk 处理模块、embedding 适配器、向量存储边界和异步任务编排
- Affected data: chunk 元数据结构、embedding 任务状态、pgvector 行模型、向量重建标记和批处理配置
- Affected dependencies: Embedding Model 提供方、pgvector 持久化策略、批量向量化接口和配置管理
- Affected processing flow: 统一 Markdown 产物将从 Parser Service 交给 Embedding Pipeline，而不是在单个处理 service 中内联完成
- No scope change to retrieval UX: 不改变当前前端原型、资料上传入口、面试页面和实时回答交互
