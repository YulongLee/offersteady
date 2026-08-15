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
- 展示名称与原始文件名分离：同一账号、同一资料类型出现重名时，展示名称在扩展名前自动追加编号；用户重命名只修改展示名称，不修改原文件或历史回答快照。
- 用户可以在资料管理页和面试准备页下载自己上传的原文件。下载必须先由后端校验账号归属，再返回附件内容与原始文件名；前端不得使用公开对象地址或暴露私有 OSS key。
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
- `material_knowledge_collections`：用户知识资料库元数据；重命名由后端持久化，删除使用 `deleted_at_ms` 软删除，并同步软删除库内文档。

## 处理与索引流程

1. 后端签发 upload intent，生成 `documentId`、`documentVersionId`、`objectId` 与 OSS key。
2. 客户端直传 OSS；知识材料随后调用 quote，后端校验 intent、用户、object key、content type、大小与可选 `contentSha256`。
3. 知识材料 quote 阶段由 Parser 读取原始对象、输出标准 Markdown 并保存到 `processed/normalized.md`，再按规范化 UTF-8 正文估算 Token。PDF 图片、字体、压缩流等容器字节不得进入报价。
4. 客户端展示服务端最终 Token、计费单位、点数或会员额度、预计余额和目录版本；用户确认后携带与当前 `documentVersionId` 绑定的 `quoteId` 调用 complete。
5. 后端预留报价快照对应的积分或额度，保存文档记录，并让正式处理复用 quote 阶段的 `processed/normalized.md`，避免重复解析 PDF。
6. Chunker 生成 chunk manifest，保存到 `processed/chunks.jsonl`。
7. Embedding pipeline 写入 pgvector；向量行必须带 owner/document/version/kind/collection/model 元数据。
8. 成功后文档进入 `ready/indexed`，失败进入 `failed`，不会进入会话可选列表。

## RAG 会话边界

面试会话只能检索本场确认的资料快照：

- 检索 filter 必须包含 `ownerUserId`。
- live/screenshot 回答必须传入当前 session 的 `documentIds` 与 `documentVersionIds` allowlist。
- `deleted`、`disabled`、非 `ready/indexed` 资料不会参与检索。
- 没有命中资料时，prompt 必须提示模型只能给通用表达，不得编造候选人的项目、公司、职责、结果或数字。

## 索引计费

知识资料索引按报价、确认、结算、释放四阶段处理：

- quote 记录 token estimate、catalog version、tokenizer version、points required、projected balance。
- token estimate 只能来自服务端 Parser 的规范化可索引 Markdown；禁止使用原始文件大小或客户端估算作为真实报价。当前 `mvp-v1` 为规范化 UTF-8 正文字节数除以 4 后向上取整。
- quote 必须绑定 owner 与 `documentVersionId`；Web 上传先 quote、展示最终价格，再携带 `quoteId` complete。
- reserve 只能在用户显式确认报价后发生。
- settle 只能在可用 pgvector index 交付后发生，并通过 reference ID 保证幂等。
- parse、embedding、pgvector、timeout 或 cancellation 失败时 release reservation。
- 有有效会员知识资料额度时优先锁定 1 份额度，成功后从 locked 转为 used；否则预留积分并在成功后写入 `knowledge_index_settlement` 负数账本。
- 完成上传请求必须携带显式计费确认；同一 `documentVersionId` 的完成重放或 worker 重试不得重复扣点或重复消耗额度。

## 日志与隐私

日志不得包含原始文档文本、截图内容、完整 prompt、embedding、OSS object key、provider payload 或环境密钥。相关字段必须经过 `redact_log_value` 过滤。
