## Context

OfferSteady 现有 Web 原型已经形成“资料页 -> 创建面试 -> 准备页选择资料 -> 实时回答/截图回答”的主路径，后端也已经建立 FastAPI、OSS、PostgreSQL、pgvector、Document Service、Parser、Embedding、Retrieval、Chat 和端到端联调的模块边界。但当前能力仍分散在多个 change 和骨架实现中，资料上传、解析、索引、计费和面试回答之间缺少一个可商业化使用的事实源闭环。

本设计承接现有原型，不重排页面。重点是把资料生命周期从“可演示状态”升级为“后端可恢复、可删除、可审计、可检索、可计费”的生产路径。`.env` / `.env.local` 中的 OSS、数据库、模型和检索配置只由后端读取；浏览器继续只读取 `VITE_` 公开变量。

## Goals / Non-Goals

**Goals:**

- 让 Resume、JD、Knowledge 文档真实上传到 OSS，并在 PostgreSQL 中保存用户范围内的元数据、版本、状态和删除信息。
- 定义稳定 OSS 对象键规范，覆盖环境、用户、文档类型、文档 ID、版本、原始文件、解析产物和临时产物。
- 实现文档处理流水线：解析、Markdown 标准化、Chunk、Embedding、pgvector 写入、状态回写和失败恢复。
- 让准备页只能选择后端确认的 ready、indexed、non-deleted、non-disabled 文档版本，并保存会话级不可变资料快照。
- 让实时文字回答和截图回答按本场资料快照进行 RAG 检索，回答中展示安全来源摘要和版本，不泄露原始全文、Prompt 或密钥。
- 保持现有计费规则：上传不直接扣点，索引成功后结算，失败释放，重复内容或幂等重试不重复扣点。

**Non-Goals:**

- 不重新设计资料页、准备页、实时面试页或截图回答入口。
- 不实现新的支付渠道、会员价格或兑换码规则。
- 不把资料选择搬到实时页；实时页继续使用准备页确认的资料快照。
- 不把 OSS、数据库、Embedding、Rerank、Chat 或 Vision 密钥暴露到前端。
- 不承诺长期保存完整音频或自动保存用户未确认的敏感采集内容。

## Decisions

### 1. PostgreSQL remains the transactional source of truth; OSS only stores objects

所有资料文档的归属、版本、状态、删除、处理任务、索引用量和会话选择都以 PostgreSQL 为事实源。OSS 只保存原始文件、解析产物和临时导出对象，业务判断不得依赖遍历 OSS。

备选方案是把 OSS 对象列表当作文档库，但这会让权限、状态、计费和删除审计变得不可控，也不适合商业化账务和多用户隔离。

### 2. OSS object keys are opaque, environment-scoped and versioned

对象键使用以下规范：

```text
{key_prefix}/{env}/users/{user_id_hash}/documents/{document_kind}/{document_id}/versions/{version_id}/original/{object_id}.{ext}
{key_prefix}/{env}/users/{user_id_hash}/documents/{document_kind}/{document_id}/versions/{version_id}/processed/normalized.md
{key_prefix}/{env}/users/{user_id_hash}/documents/{document_kind}/{document_id}/versions/{version_id}/processed/chunks.jsonl
{key_prefix}/{env}/users/{user_id_hash}/documents/{document_kind}/{document_id}/versions/{version_id}/deletion-marker.json
{key_prefix}/{env}/tmp/uploads/{upload_intent_id}/{object_id}.{ext}
{key_prefix}/{env}/exports/{user_id_hash}/{export_id}/{object_id}
```

`user_id_hash` 使用服务端不可逆摘要或内部短 ID，避免在对象路径中暴露可识别账号信息。`document_id`、`version_id`、`object_id` 使用服务端生成的不可猜测 ID。同名文件只影响 `display_name`，不影响对象键。

备选方案是按原始文件名和日期建路径。它便于人工查看，但容易泄露候选人姓名、公司、岗位和文件内容语义，也容易发生覆盖或误删。

### 3. Upload, processing and indexing use separate state machines

Document Service 负责 `upload_intent -> uploaded -> processing_requested -> deleted` 的文档事实；Processing Pipeline 负责 `queued -> parsing -> normalizing -> chunking -> embedding -> indexing -> indexed/failed` 的任务事实；Billing Usage 负责报价、预留、结算和释放。

这样可以让上传成功但索引失败的资料仍保留为非可选状态，并允许用户重试、替换、删除或充值后继续。备选方案是上传请求同步完成解析索引；实现直观，但大文件和外部供应商耗时会导致页面阻塞、重试困难和重复扣费风险。

### 4. pgvector stores chunk embeddings with strict retrieval filters

每个 chunk 记录 `user_id`、`document_id`、`version_id`、`document_kind`、`collection_id`、`chunk_id`、`content_hash`、`embedding_model`、`embedding_dimension`、`created_at` 和安全摘要。检索时必须同时过滤 `user_id` 和会话确认的 `version_id` 白名单，不能只按关键词或 collection 查询。

备选方案是按用户全库检索后在应用层过滤。该方案可能在日志、rerank 或模型上下文里提前暴露未授权资料，不符合准备页确认清单的产品边界。

### 5. Session material snapshots are immutable after confirmation until user reconfirms

准备页确认资料时，Session Service 保存 `selection_revision` 和每个来源的 `document_id/version_id/display_name/kind/index_state/deleted_marker` 快照。实时回答和截图回答只使用当前确认 revision；资料库后续新增、替换或删除不会静默改变已确认会话。

如果来源被删除，未来检索立即失效；历史回答只保留最小来源标签、版本和删除标记。备选方案是实时读取资料库最新状态自动替换来源，但这会破坏用户授权边界，也让回答来源不可追溯。

### 6. RAG orchestration returns safe context, not raw document dumps

Retrieval Service 返回结构化上下文：短摘要、相关片段、来源标签、版本、置信度、检索/重排分数和截断信息。Chat/Screenshot Answer Service 使用这些结构化上下文拼接 Prompt，但流式事件和普通日志不得输出全文资料、完整 Prompt、Embedding 请求正文或供应商原始 payload。

备选方案是直接把完整 Markdown 或全文片段传给模型和前端。它实现快，但会增加隐私泄露、成本失控和幻觉来源混淆风险。

### 7. Commercial metering settles on usable index delivery

知识资料索引使用现有价格目录：上传和创建空集合不扣点；报价基于解析后 token 估计；确认后预留积分或会员知识额度；只有可用索引写入 pgvector 并标记 indexed 后才结算。失败、取消、超时、重复内容和幂等重放释放预留或复用既有结果。

备选方案是在上传时扣费。这个方案容易让用户为失败解析、空内容或重复文件付费，商业信任风险太高。

## Risks / Trade-offs

- [Risk] 真实 OSS / Parser / Embedding / pgvector 链路引入更多失败点 → Mitigation: 每一步持久化任务状态，提供重试、替换、删除和安全错误文案。
- [Risk] RAG 结果与用户期待不一致 → Mitigation: 回答展示来源标签和“建议”边界，不把检索结果包装成事实保证。
- [Risk] 文档内容进入日志或报告 → Mitigation: 只记录 ID、状态、大小、token 估计、耗时和错误码；集成报告使用脱敏摘要。
- [Risk] 大文件索引成本不可控 → Mitigation: 在报价前做格式、大小、页数/字符数和 token 上限校验，超限要求显式确认或拒绝。
- [Risk] 删除资料破坏历史复盘 → Mitigation: 删除后未来检索立即失效，历史回答只保留最小来源墓碑，不恢复内容。
- [Risk] 多个旧 change 已覆盖部分骨架 → Mitigation: 本 change 不重新定义已完成底座，只把真实商业化闭环作为实现收口，并在任务中复用既有模块。

## Migration Plan

1. 增加 PostgreSQL 表和 repository：documents、document_versions、upload_intents、processing_jobs、document_chunks、index_jobs、session_material_snapshots、deletion_jobs。
2. 接入 OSS 对象键生成器和上传完成校验，迁移现有内存文档状态到数据库事实源。
3. 将 Parser / Normalizer / Chunker / Embedding / pgvector 写入接入处理流水线，先支持 PDF、DOCX、DOC、TXT、MD。
4. 接入索引报价、预留、结算和失败释放，确保幂等键和内容指纹生效。
5. 改造 `/api/v1/web/state`、资料页 adapter 和准备页 adapter，使页面读取后端持久化状态但不改变原型布局。
6. 改造 Session Service、Chat Service、Screenshot Answer Service，使回答只检索本场确认资料快照。
7. 增加 OSS/PostgreSQL/pgvector/RAG 全链路联调脚本，使用 `.env` / `.env.local` 的真实配置和脱敏样本。
8. 回滚时保留已上传对象和数据库元数据，关闭索引 worker 与 RAG 使用开关，前端显示上传资料处理中或不可用，不删除用户数据。

## Open Questions

- 生产环境首版是否只允许单文件 50 MB / 50 页，还是要按商业套餐配置不同上限？
- MinerU 或解析供应商失败时，是否允许 TXT/MD 走本地轻量解析直接进入索引？
- pgvector embedding dimension 是否固定为当前 `.env` 模型，还是需要按模型版本多列/多表支持迁移？
- 是否需要为企业/多租户预留 `tenant_id`，即使当前只有个人账号？
