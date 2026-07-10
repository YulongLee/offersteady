## Why

当前系统已经建立统一 Document Service、Document Parser Service 和 Embedding Pipeline，文档内容可以被解析并写入向量存储，但还缺少真正把这些向量数据转化为“可供问答使用的知识上下文”的统一检索层。现在需要建立独立的 Knowledge Retrieval Service，把 Query Embedding、向量召回、metadata 过滤、TopK、Reranker 和 Context Builder 收敛成一个统一服务，为后续 Chat Service 提供稳定的 RAG 输入。

## What Changes

- 新增独立的 Knowledge Retrieval Service，统一负责用户问题到知识上下文的检索流程。
- 支持 Resume、JD、Knowledge Base 联合检索，并通过 metadata 做范围过滤。
- 定义 Query Embedding、Vector Search、Metadata Filter、TopK、Reranker、Context Builder 和 Retrieval API 的模块边界。
- 支持不同检索策略、不同 TopK 配置和可替换的 reranker / retrieval provider。
- 明确 Retrieval Service 与 Chat Service 解耦：Retrieval 只返回结构化上下文，不负责 Prompt 拼接或 LLM 调用。
- 本次只覆盖检索与上下文构建链路，不实现 Chat Service、Prompt 拼接或模型生成。

## Capabilities

### New Capabilities
- `knowledge-retrieval-service`: 定义统一问题嵌入、向量召回、metadata 过滤、重排序和上下文构建能力

### Modified Capabilities
- None

## Impact

- Affected backend: `apps/backend` 的 retrieval service、query embedding、pgvector search、reranker 和 retrieval API
- Affected data: 检索结果结构、metadata 过滤条件、TopK 配置、context 片段组织方式和日志字段
- Affected dependencies: Query embedding provider、pgvector similarity search、reranker provider 与可配置检索策略
- Affected AI flow: 后续 Chat Service 将从 Retrieval Service 获取结构化上下文，而不是直接操作向量库
- No scope change to chat UX: 不改变当前前端原型、上传入口、面试页面或回答区交互
