## Why

当前产品原型已经具备资料页、准备页、实时面试页和后端上传/检索/回答模块骨架，但真实商业化使用仍缺少一条完整闭环：用户上传的简历、JD 和知识材料必须可靠进入 OSS、PostgreSQL 与 pgvector，并能在面试时按用户确认的资料清单参与 RAG 回答。

现在需要把已有分散能力收束成可上线的资料与 RAG 持久化链路，避免资料只停留在前端状态或内存服务里，也避免 OSS、数据库、索引、计费和面试选择各自形成不一致的事实源。

## What Changes

- 建立商业化资料库的后端事实源，覆盖 Resume、JD、Knowledge 文档上传、OSS 对象键、PostgreSQL 元数据、版本、状态、软删除、异步清理和审计字段。
- 设计并实现稳定的 OSS 存储路径规范，区分原始上传、解析产物、导出/临时产物和删除清理标记，确保同名文件不覆盖、跨用户不可猜测、可按环境和租户隔离。
- 将 Document Processing Pipeline 从上传后状态推进到真实解析、Markdown 标准化、Chunk、Embedding、pgvector 写入和索引状态回写。
- 完成 RAG 检索服务的商业化路径：按用户、会话、文档类型、文档版本和本场确认资料过滤检索，返回带来源标签的安全上下文。
- 在准备页继续保持现有原型交互，但将资料可选性升级为后端确认的 ready / non-deleted / indexed 版本；本场资料选择保存不可变快照。
- 在实时面试回答和截图回答中使用本场确认资料进行检索增强，回答中保留来源摘要、版本和删除标记，不暴露原始全文或内部 Prompt。
- 接入现有计费规则：资料索引报价、预留、成功结算、失败释放、重复内容幂等复用和会员知识材料额度都以服务端事实源为准。
- 保持现有 Web 原型页面结构、主路径和交互顺序不变；只补数据来源、状态、错误恢复和真实后端联调能力。
- 不把 OSS、数据库、模型或嵌入密钥暴露给浏览器；本地 `.env` / `.env.local` 只由后端读取。

## Capabilities

### New Capabilities

- `commercial-material-persistence`: 商业化资料上传、OSS 对象路径、PostgreSQL 元数据、版本、状态、删除和审计边界。
- `document-processing-indexing-pipeline`: 文档解析、Markdown 标准化、Chunk、Embedding、pgvector 写入、索引任务状态和失败恢复。
- `session-rag-grounded-answering`: 面试会话按确认资料清单进行 RAG 检索，并将来源增强用于实时回答和截图回答。

### Modified Capabilities

- `streamlined-interview-entry`: 准备页资料选择必须来自后端持久化资料库，并且只有已索引、未删除、未停用的 ready 版本可被确认为本场资料。

## Impact

- `apps/backend`: 文档服务、知识资料服务、处理流水线、检索服务、Chat Service、Screenshot Answer Service、Session Service、计费用量、数据库 repository 和 OSS 适配器。
- `apps/web`: 资料页、准备页、实时回答和截图回答的 adapter 联调，不改变已批准原型结构。
- `packages/protocol`: 资料版本、上传意图、处理任务、索引任务、RAG 来源、会话资料快照和错误状态协议。
- `infra`: PostgreSQL 表结构、pgvector 索引、迁移脚本、OSS bucket/key prefix 约定和本地/生产环境变量。
- `ai/prompts` 与 `ai/evals`: 需要补充资料来源约束、RAG grounded answer 行为和敏感内容不泄露评测。
- 外部系统：Aliyun OSS、PostgreSQL、pgvector、文档解析 Provider、Embedding Provider、Rerank Provider 和 Qwen-compatible Chat/Vision Provider。
- 隐私影响：简历、JD 和知识材料将从原型状态升级为持久化敏感数据，必须支持授权访问、删除、最小日志、历史来源墓碑和测试数据脱敏。
