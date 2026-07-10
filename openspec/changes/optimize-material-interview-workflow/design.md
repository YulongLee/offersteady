## Context

OfferSteady 当前已经具备资料上传、OSS 存储、MinerU 转换、embedding/rerank、Postgres 资料持久化、面试会话和回答生成模块，但产品链路仍被用户感知为“不拉通”：资料库里有文件，创建面试也能选择资料，但绑定慢、重启后会话绑定可能丢失，回答结果也可能表现为没有使用资料。

核心约束是产品仍处于原型与 MVP 验证阶段，不能为了局部体验提前引入不可替换的复杂平台；同时资料、简历、JD、截图和音频都属于敏感数据，客户端不得保存服务端密钥或直接访问 OSS、Embedding、Rerank、Chat Provider。

## Goals / Non-Goals

**Goals:**

- 把资料上传后的重处理前移到资料库后台，形成后端可复用资料能力。
- 让创建面试和准备页绑定资料保持轻量、快速、可解释。
- 以数据库中的 document/version/selectable 状态作为准备页主要事实源，避免用户点击确认时同步执行重型 OSS/MinerU/向量处理。
- 保证前端资料列表、后端资料记录和 OSS artifacts 之间存在可解释的一致性：前端不展示无法由后端解释的资料，后端不把缺失关键 OSS 产物的资料标记为可用。
- 保留回答前 fail-closed 校验，确保资料失效时不会伪装成已使用资料。
- 明确简历/JD 固定上下文和知识库 RAG 上下文的边界。
- 让用户能看到资料处理状态、绑定状态、回答来源和不可用原因。

**Non-Goals:**

- 不把简历/JD 默认改成 RAG-only 来源。
- 不在浏览器端暴露 OSS、MinerU、Embedding、Rerank 或 Chat Provider 密钥。
- 不新增复杂资料编辑器、全文预览器或人工标注系统。
- 不承诺所有上传格式都能完美解析；失败必须可见、可重试。
- 不默认读取用户资料库中所有资料；回答只使用本场确认快照。

## Decisions

### 1. Move heavy material work to the library processing pipeline

资料上传完成后，后端异步执行 OSS artifact 校验、MinerU 转 Markdown、Markdown 归一化、chunk 生成、embedding、向量入库和数据库状态更新。准备页只消费 `ready/indexed/selectable` 的结果。

替代方案是在创建面试时同步检查 OSS、重新转换或补建索引。该方案看起来更保险，但会让“确认本场资料”变慢，并把资料处理失败暴露在面试开始这一关键路径上，不适合面试前高压场景。

### 2. Use database selectable state as the preparation-page source of truth

资料库页和准备页都从后端资料记录读取同一套状态：document ID、version ID、kind、display name、status、index state、selectable、unavailable reason。准备页确认时只做 ownership、kind、status、index state 和 selectable 的轻量校验，并保存 session material snapshot。

替代方案是准备页每次打开都扫描 OSS artifacts。该方案能发现极少数外部删除，但网络慢且成本高。当前选择是在资料处理完成时强校验 OSS，在回答前读取时兜底失败。

### 3. Treat database as frontend source of truth and OSS as artifact source of truth

前端资料库列表只读取后端 API，不直接列 OSS bucket。后端数据库记录每个 document/version 对应的 original、normalized Markdown、chunks 和 vector index 状态。新增资料时先创建 upload intent，再在 OSS 上传完成后登记数据库并进入处理；删除资料时先在数据库标记 deleted/unselectable，再调度 OSS 原始文件、processed artifacts 和向量记录清理。

替代方案是前端直接读取 OSS 或 OSS 作为唯一资料列表。该方案看似“同步”，但无法表达处理状态、索引状态、用户权限、软删除、失败原因和会话快照，不适合商业化产品。

### 4. Persist session material snapshots by document version

确认本场资料后，后端保存 session 级快照，包含 resume document/version、JD document/version、knowledge document/version 列表和确认时间。回答服务只使用该快照，不自动拉取资料库中新上传或修改但未确认的资料。

替代方案是回答时读取资料库最新状态。该方案减少确认步骤，但会导致用户无法解释“为什么这场面试突然用了别的资料”，也不利于复盘和审计。

### 5. Keep answer-time fail-closed validation

虽然准备页不做重型 OSS 校验，回答生成前仍要加载固定资料 Markdown 和检索知识库 chunks。如果已确认资料无法读取或检索，回答任务必须记录 unavailable source，并要求模型说明没有使用该资料，不能泛答后伪装成基于资料。

替代方案是完全相信数据库状态。该方案最快，但如果用户或后台删除了 OSS 产物，会产生“看似使用资料、实际没用”的商业化风险。

### 6. Separate fixed context and RAG context

简历和 JD 作为固定上下文注入 Prompt；知识库通过 embedding 检索和 rerank 后注入。回答 provenance 分别统计 fixed sources 和 retrieved sources，避免把 `retrieved=0` 误判为简历/JD 没使用。

替代方案是把所有资料都放进 RAG。该方案统一，但会让“我的优势是什么”“结合我的简历回答”这类问题受到召回遗漏影响。

### 7. Design OSS paths around user, document, version, and artifact role

OSS 路径以环境、用户哈希、document kind、document ID、version ID 和 artifact role 分层。数据库保存 object key、version、fingerprint 和 artifact verification 状态；前端永远不直接依赖 OSS key。

替代方案是使用扁平文件名或用户可见名称作为路径。该方案调试直观，但重名、版本回滚、删除和权限隔离风险更高。

## Risks / Trade-offs

- [Risk] 数据库 selectable 状态与 OSS 实际状态短暂不一致 → Mitigation: 资料处理完成时做 artifact 校验，回答前 fail-closed 读取校验，后台可补充异步健康扫描。
- [Risk] OSS 手工删除导致前端仍显示旧资料 → Mitigation: 后端后台同步校验将资料标记为 stale/unselectable；回答前读取失败必须降级；资料库提供重新同步入口。
- [Risk] 删除请求中 OSS 清理失败 → Mitigation: 数据库先标记 deleted/unselectable，后续 deletion job 重试 OSS 和向量清理，前端不再展示为可用资料。
- [Risk] 上传阶段变慢，用户以为卡住 → Mitigation: 资料库展示 processing/artifact-ready/indexing/ready 进度和失败原因，不阻塞其他页面使用。
- [Risk] 知识库 RAG 无命中时用户误以为没加载资料 → Mitigation: provenance 区分 fixed context、retrieved context、no match 和 unavailable。
- [Risk] 旧会话引用已删除资料 → Mitigation: 准备页重新进入时标记失效，回答时排除失效来源并显示不可用原因。
- [Risk] 外部 MinerU、Embedding、Rerank 供应商波动 → Mitigation: 保持适配器边界，任务可重试，失败安全落库。

## Migration Plan

1. 梳理当前资料状态字段和 session binding 字段，补齐 selectable/unavailable reason/artifact verification 和 sync status。
2. 将资料处理完成的 OSS artifact 校验前移到 processing pipeline，记录 normalized Markdown、chunks 和 vector index 状态。
3. 将准备页确认资料改为轻量后端绑定，仅依赖数据库可选状态，不同步执行重型 OSS 扫描。
4. 实现新增和删除的同步策略：新增以 upload intent + completion 为准，删除以数据库 tombstone + OSS/vector deletion job 为准。
5. 持久化 session material snapshot，并确保 Web state、实时回答、截图回答均读取该快照。
6. 优化回答 provenance 和前端文案，统一使用“已选资料/资料库内容”而非含糊的“个人资料”。
7. 增加端到端联调脚本：上传资料、处理完成、创建面试、选择资料、提问、检查来源。
8. 回滚时保留资料库数据和 OSS artifacts，只回退准备页绑定逻辑和 provenance 展示，不删除用户资料。

## Open Questions

- 资料处理阶段是否需要在原型阶段实现后台定时 OSS 健康扫描和手动“重新同步”入口，还是先依赖处理完成校验和回答前兜底？
- 资料库中简历/JD 是否也需要构建向量索引用于未来搜索，还是首版只保留固定上下文所需 Markdown？
- 准备页是否允许选择 knowledge-only 面试并在 UI 明确说明无法回答候选人个人经历问题？

## Commercial Architecture Amendment

商业化版本 SHOULD split API requests from long-running material work. FastAPI handles authentication, request validation, session material confirmation, answer task creation and state queries. A Worker/Queue layer handles MinerU parsing, Markdown normalization, chunking, embedding, vector indexing, OSS/DB reconciliation and deletion cleanup.

The system SHOULD persist explicit artifact manifest records for each material document version. Each ready/selectable document version should be explainable through database state and verified OSS artifacts rather than implicit path conventions only.

The system SHOULD persist processing, deletion and reconciliation jobs with retry counts and safe error codes. This is required for user-facing reliability, support diagnostics and commercial operations.

The system SHOULD keep model responsibilities separated through adapters: MinerU for parsing, qwen3-vl for screenshot/photo recognition, text-embedding-v3 for embeddings, qwen3-rerank for reranking and deepseek-v4-flash for final answer generation. These adapters must remain backend-only and configurable without exposing provider credentials to the frontend.

The system SHOULD record safe AI usage and RAG retrieval traces for billing, cost control and debugging. These records must not store raw resume text, JD text, screenshot images, full prompts, embeddings or provider payloads.
