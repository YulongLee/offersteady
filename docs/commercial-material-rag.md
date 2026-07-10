# 商业化资料存储与 RAG 设计

本文件记录面试稳资料库商业化链路的长期约定。当前仍处于产品原型阶段，实现优先保持简单、可替换，但后端已经按商业化边界保存关键元数据。

## OSS 对象路径

所有用户资料对象只在后端生成 key，前端不得拼接路径或保存服务端密钥。

路径格式：

```text
{ossKeyPrefix}/{environment}/users/{userHash}/documents/{kind}/{documentId}/versions/{documentVersionId}/original/{objectId}.{ext}
{ossKeyPrefix}/{environment}/users/{userHash}/documents/{kind}/{documentId}/versions/{documentVersionId}/processed/normalized.md
{ossKeyPrefix}/{environment}/users/{userHash}/documents/{kind}/{documentId}/versions/{documentVersionId}/processed/chunks.jsonl
{ossKeyPrefix}/{environment}/users/{userHash}/documents/{kind}/{documentId}/versions/{documentVersionId}/deleted/{deletedAtMs}.json
{ossKeyPrefix}/{environment}/users/{userHash}/tmp/{uploadIntentId}/{objectId}.{ext}
{ossKeyPrefix}/{environment}/users/{userHash}/exports/{exportId}/{objectId}.json
```

约定：

- `userHash` 使用 `MATERIAL_USER_HASH_SALT` 与用户 ID 计算，不暴露原始用户 ID。
- `environment` 优先使用 `OFFERSTEADY_OSS_ENVIRONMENT_LABEL`，否则使用 `OFFERSTEADY_ENVIRONMENT`。
- 原始文件名只作为展示名与元数据保存，不进入 OSS key。
- 删除动作先创建 deletion job，记录 raw object、processed artifact、deletion marker 和向量删除过滤条件。

## 数据库表

迁移 `0003_commercial_material_rag_persistence.sql` 定义商业化资料链路表：

- `material_documents`：用户维度文档主记录，保存当前版本、类型、集合、删除状态。
- `material_document_versions`：文档版本，保存 OSS object、content fingerprint、解析/索引状态与统计。
- `material_upload_intents`：上传意图，绑定用户、对象 key、过期时间与确认状态。
- `material_processing_jobs`：解析、Markdown 标准化、chunk、embedding、indexing 阶段任务。
- `material_index_jobs`：索引计费和 pgvector 写入任务。
- `material_document_chunks`：pgvector chunk 行，必须包含 owner、document、version、kind、collection、embedding model 元数据。
- `session_material_snapshots`：面试开始前确认的不可变资料快照。
- `material_deletion_jobs`：异步删除 OSS 对象、processed artifact 与向量行的审计 job。

## 处理与索引流程

1. 后端签发 upload intent，生成 `documentId`、`documentVersionId`、`objectId` 与 OSS key。
2. 客户端直传 OSS 后调用 complete，后端校验 intent、用户、object key、content type、大小与可选 `contentSha256`。
3. 后端保存文档记录，`indexState` 从 `queued` 进入 `processing`。
4. Parser 读取原始对象，输出标准 Markdown，并保存到 `processed/normalized.md`。
5. Chunker 生成 chunk manifest，保存到 `processed/chunks.jsonl`。
6. Embedding pipeline 写入 pgvector；向量行必须带 owner/document/version/kind/collection/model 元数据。
7. 成功后文档进入 `ready/indexed`，失败进入 `failed`，不会进入会话可选列表。

## RAG 会话边界

面试会话只能检索本场确认的资料快照：

- 检索 filter 必须包含 `ownerUserId`。
- live/screenshot 回答必须传入当前 session 的 `documentIds` 与 `documentVersionIds` allowlist。
- `deleted`、`disabled`、非 `ready/indexed` 资料不会参与检索。
- 没有命中资料时，prompt 必须提示模型只能给通用表达，不得编造候选人的项目、公司、职责、结果或数字。

## 索引计费

知识资料索引按报价、确认、结算、释放四阶段处理：

- quote 记录 token estimate、catalog version、tokenizer version、points required、projected balance。
- reserve 只能在用户显式确认报价后发生。
- settle 只能在可用 pgvector index 交付后发生，并通过 reference ID 保证幂等。
- parse、embedding、pgvector、timeout 或 cancellation 失败时 release reservation。

## 日志与隐私

日志不得包含原始文档文本、截图内容、完整 prompt、embedding、OSS object key、provider payload 或环境密钥。相关字段必须经过 `redact_log_value` 过滤。
