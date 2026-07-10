## Context

当前系统已经具备统一 Document Service、Document Parser Service 和 Embedding Pipeline，文档内容可以被解析成 Markdown 并写入向量存储，但从“用户问题”到“可供问答使用的知识上下文”之间还缺少独立的检索层。随着后续 Chat Service 需要基于 Resume、JD 和 Knowledge Base 做联合检索与上下文构建，当前最自然的下一步就是建立独立的 Knowledge Retrieval Service。

当前这层能力需要满足几个前提：

- 不改变前端原型、上传流程和面试页面交互
- 支持 Resume、JD、Knowledge Base 联合检索
- 检索层要与 Chat Service 解耦，只返回结构化上下文
- 需要支持 metadata 过滤、不同检索策略、TopK 配置和可替换 reranker
- 日志、召回结果和调试信息不能泄露过量敏感正文

## Goals / Non-Goals

**Goals:**

- 建立独立的 Knowledge Retrieval Service，统一负责 query embedding、向量召回、metadata 过滤、TopK、reranker 和 context builder
- 支持 Resume、JD、Knowledge Base 联合检索
- 支持 metadata filter、不同检索策略和可配置 TopK
- 提供 Retrieval API，返回结构化上下文供 Chat Service 或其他上层服务消费
- 保持 query embedding、vector search、reranker 提供方可替换
- 增加 Retrieval 日志和可观测性约定

**Non-Goals:**

- 不实现 Chat Service
- 不实现 Prompt 拼接
- 不实现 LLM 调用
- 不改动前端原型结构或交互顺序

## Decisions

### 1. 采用“Retrieval Service 返回上下文，Chat Service 消费上下文”的边界

Knowledge Retrieval Service 只负责从问题生成上下文，不负责拼 Prompt 或调用 LLM。输出应是结构化的 retrieval result，包括召回片段、来源信息、得分和汇总后的 context block。

原因：

- 保持检索层与生成层解耦
- 让 Chat Service 可以独立迭代 Prompt 和模型逻辑
- 使检索能力也能被其他流程复用，例如面试准备预览或知识命中检查

备选方案：

- 直接在检索服务里拼 Prompt：实现更快，但会把检索与生成策略耦合在一起

### 2. 检索流程固定为“Query Embedding → Vector Search → Metadata Filter → TopK → Reranker → Context Builder”

Retrieval Service 的标准流程固定为：

1. Query Embedding
2. pgvector Similarity Search
3. Metadata Filter
4. TopK Recall
5. Reranker
6. Context Builder
7. Return Context

原因：

- 让 query 向量生成和候选召回有稳定边界
- 保持 reranker 是可选增强，而不是和向量搜索混写
- 让 context builder 专门负责把片段组织为上层可消费的上下文

备选方案：

- 直接在向量搜索后返回原始片段：实现快，但会让上层重复处理过滤、排序和上下文拼装

### 3. 联合检索基于统一向量表 + metadata 过滤完成

Resume、JD、Knowledge Base 都从统一向量来源检索，但必须通过 metadata 支持过滤维度，例如：

- document_kind
- owner_user_id
- interview_session_id
- knowledge_collection_id
- rebuild_version / active_version

原因：

- 便于统一执行多源联合检索
- 允许不同面试场次选择不同上下文范围
- 与 Embedding Pipeline 当前的统一 metadata 方向一致

备选方案：

- 分别对三个知识源调用三套检索接口再合并：灵活，但重复逻辑多且排序更复杂

### 4. Query Embedding 与 Document Embedding 分离为独立 provider 边界

Query Embedding 不直接复用文档向量化编排逻辑，而是提供独立的 query embedding 端口。它可以与 document embedding 使用同一模型，也可以不同。

原因：

- 某些部署会选择 query / document 双塔模型或不同 provider
- 检索时延要求与离线文档 embedding 不同
- 更利于后续优化查询成本和吞吐

备选方案：

- 直接强制 query 和 document 用同一个 embedding 入口：简单，但限制未来策略

### 5. Reranker 作为可插拔增强层，而不是强制阶段

Retrieval Service 支持在 TopK 之后引入 reranker，但 reranker 可以配置为：

- disabled
- heuristic reranker
- model-based reranker

原因：

- 允许 MVP 先用简单策略运行
- 后续在不破坏检索 API 的前提下增强结果质量
- 让不同成本/时延环境可以切换策略

备选方案：

- 强制每次都使用 model-based reranker：质量可能更好，但成本和时延更高

### 6. Context Builder 返回结构化片段和汇总文本两种视图

Retrieval 返回建议至少包含：

- normalized question
- recalled chunks
- source metadata
- similarity / rerank scores
- context_text（供上层直接消费）

原因：

- 让上层既能直接拿字符串上下文，也能保留结构化证据链
- 方便调试和后续 UI / 运营分析扩展

备选方案：

- 只返回一段拼好的字符串：对 Chat Service 方便，但不利于可观测和可追溯性

### 7. TopK、过滤和策略通过运行时配置驱动

至少需要支持以下可配置项：

- candidate_top_k
- final_top_k
- min_score_threshold
- reranker_enabled
- retrieval_strategy（single-pass / hybrid-ready / filtered-first）

原因：

- 检索策略经常需要线上迭代
- 不同文档类型和场景可能需要不同召回深度
- 防止检索逻辑被硬编码在 API handler 中

备选方案：

- 全部写死在 service：实现快，但后续调整成本高

### 8. 检索日志记录元信息和分数，不记录完整敏感正文

Retrieval 日志允许记录：

- request_id
- session_id
- question_hash 或 question_length
- candidate_count
- final_count
- filters
- top_k
- provider_name
- duration_ms

禁止记录：

- 用户完整问题原文（普通日志中）
- full context 全文
- 大段 Resume / JD / Knowledge 命中文本

原因：

- 满足敏感资料最小暴露原则
- 保持足够的排障和效果分析上下文

备选方案：

- 直接记录全部召回片段：调试方便，但隐私风险太高

## Risks / Trade-offs

- [Risk] 联合检索会让 Resume / JD / Knowledge 的相关性竞争，导致某一类来源被淹没 → Mitigation: 通过 metadata filter、source balancing 或 reranker 保持可调
- [Risk] Query embedding 与 document embedding 模型不匹配影响召回效果 → Mitigation: 保持 query embedding provider 独立，并记录版本信息
- [Risk] Reranker 带来额外时延 → Mitigation: 允许关闭 reranker，并通过 TopK 配置控制进入重排的候选数
- [Risk] context builder 输出过长影响后续 Chat Service 成本 → Mitigation: 通过 final_top_k、context length 和 source trimming 做可配置限制
- [Risk] 过滤条件设计不足导致跨用户或跨场次误召回 → Mitigation: 将 metadata filter 作为正式输入契约，而不是可选临时参数

## Migration Plan

1. 先在 OpenSpec 中定义 Knowledge Retrieval Service 的能力、过滤、排序和 API 规则
2. 实现阶段新增 Query Embedding、Vector Search、Reranker、Context Builder 和 Retrieval API 边界
3. 将 Embedding Pipeline 产出的 metadata 作为 Retrieval Service 的主要过滤和上下文构建输入
4. 提供 Retrieval API 供后续 Chat Service 或其他上层流程调用
5. 后续再通过单独变更接入 Prompt 拼接、Chat Service 和 LLM 调用

## Open Questions

- 第一版 reranker 是启用启发式排序，还是直接预留 model-based reranker 接口但默认关闭？
- retrieval API 是否从第一版开始支持 source weighting，例如 Resume / JD / Knowledge 的权重偏置？
- context builder 是否需要对不同 document_kind 采用不同拼接模板？
- metadata filter 是否需要从第一版开始支持 interview_session 级白名单，而不是只支持 document_kind / collection 过滤？
