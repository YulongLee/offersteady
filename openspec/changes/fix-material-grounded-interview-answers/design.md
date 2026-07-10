## Context

当前 OfferSteady 已有资料库、上传处理、会话资料确认、实时回答、截图回答和 RAG 检索模块，但用户体验中仍存在一个关键断裂：用户在创建面试或准备页导入资料后，回答结果不一定表现出这些资料已经参与生成。尤其是简历/JD 按产品逻辑不走 RAG，而是作为固定 Prompt 上下文注入；如果回答响应只暴露 RAG 计数，用户会误以为资料没有使用。

本设计聚焦资料进入面试后的 grounding 闭环，不重新设计资料库页面或实时页。后端仍是事实源，浏览器不保存模型密钥，也不直接访问 OSS、Embedding、Rerank 或 Chat Provider。

## Goals / Non-Goals

**Goals:**

- 让准备页确认的资料快照成为实时回答和截图回答唯一的资料边界。
- 将简历/JD 固定上下文和知识库 RAG 上下文分开建模、分开记录、统一进入回答 grounding 状态。
- 当用户选择了资料但资料无法读取、检索或注入时，回答任务必须显式记录原因并向前端返回安全提示。
- 让回答结果可解释：前端能展示本次回答使用了哪些简历、JD 或知识库来源，而不是只展示 RAG chunk 数量。
- 增加可复现的端到端验证，覆盖上传资料、确认本场资料、提问、回答来源和无资料退化行为。

**Non-Goals:**

- 不改变现有资料上传格式、OSS 路径或 MinerU 转换策略。
- 不把简历/JD 改成默认 RAG 检索来源；它们仍作为本场固定资料上下文。
- 不新增新的大模型、向量库或前端直连供应商能力。
- 不承诺 AI 回答完全正确；只保证资料使用边界、来源说明和不编造约束可验证。

## Decisions

### 1. Separate fixed material context from RAG context

简历和 JD 由 Chat/Screenshot Answer Service 在回答前从本场资料快照读取 processed Markdown，截断后作为固定上下文传入 Prompt。知识库由 Retrieval Service 按本场确认的知识库版本做 embedding 检索和 rerank。

备选方案是把简历、JD 和知识库全部放入 RAG。该方案实现统一，但会让简历/JD 的关键事实被相似度召回遗漏，也会让“介绍我的经历”这类问题反而找不到固定资料。当前方案更符合面试场景：简历/JD 是本场基准事实，知识库是可检索补充资料。

### 2. Add a material context assembly result before answer generation

回答生成前先构造 `materialContextAssembly`：包含 requested sources、loaded fixed sources、retrieved knowledge chunks、unavailable sources、truncation metadata 和 safe source labels。Prompt Builder 只接收 assembly 中已校验的上下文；响应 payload 和日志只暴露安全摘要。

备选方案是继续在 Chat Service 内部临时拼字符串。它改动少，但无法解释“为什么没有使用资料”，也难以测试用户反馈的断点。

### 3. Provenance must cover fixed materials and RAG chunks

回答任务的 provenance 不只记录 RAG chunks，也要记录简历/JD 是否被注入 Prompt。前端展示“已使用：简历 v1、JD v1、知识库片段 N 条”，当只使用简历/JD 时，RAG count 可以为 0，但 fixed material count 必须大于 0。

备选方案是继续只展示 retrieval sources。这会误导用户，因为简历/JD 不经过 retrieval。

### 4. Fail closed when selected materials are unavailable

如果用户确认了资料，但回答时后端发现 processed Markdown、知识库 chunks 或向量检索不可用，系统不得静默泛答。对于可恢复问题，回答任务应返回 degraded 状态或在答案前说明哪些资料未使用；对于关键固定资料缺失，应提示用户回到资料库重新处理。

备选方案是自动忽略不可用资料继续生成。这会让用户以为回答基于资料，实际却是模型泛化，正是当前问题的根源。

### 5. Keep logs safe but make debugging possible

普通日志记录 source IDs、document/version IDs、counts、latency、assembly status 和 error codes，不记录原始资料全文、完整 Prompt、embedding、供应商 payload 或截图内容。调试和测试通过结构化响应和脱敏 eval 案例完成。

备选方案是记录完整 Prompt 排查问题。它调试快，但会泄露简历、JD 和知识库敏感内容，不适合商业化边界。

## Risks / Trade-offs

- [Risk] 增加 assembly/provenance 字段会让协议变复杂 -> Mitigation: 字段保持安全摘要级别，先覆盖回答任务响应和前端展示，不扩大到全文预览。
- [Risk] Prompt 固定上下文过长导致成本上升 -> Mitigation: 对简历/JD 做分段截断和来源标记，响应中返回 truncation metadata。
- [Risk] 用户期望知识库一定命中，但问题和资料不相关 -> Mitigation: 返回 no-match 状态并要求回答说明未使用匹配知识库，不编造。
- [Risk] 旧会话资料快照引用已删除或失败资料 -> Mitigation: 回答前重新校验 snapshot 中的 document/version 状态，返回失效来源标记。
- [Risk] 端到端测试依赖外部模型不稳定 -> Mitigation: 保留适配器边界，测试分为本地 synthetic provider 和真实 `.env` 联调两层。

## Migration Plan

1. 扩展协议类型，增加回答 material context assembly 和 provenance 字段。
2. 后端实现固定资料上下文 loader，明确 resume/JD 与 knowledge RAG 的分工。
3. Chat Service 和 Screenshot Answer Service 在生成前统一调用 assembly，并将结果传入 Prompt Builder。
4. 前端实时回答区域展示固定资料和知识库来源的使用情况，以及资料不可用提示。
5. 增加 AI prompt 约束和 eval：有资料必须优先使用资料，无资料或资料不可用不得编造经历。
6. 增加端到端验证：创建面试、选择简历/JD/知识库、提问、检查 provenance 和回答内容。
7. 回滚时保留现有资料库和会话数据，只隐藏新增 provenance 字段并恢复旧回答展示。

## Open Questions

- 简历/JD 固定上下文首版截断上限是否沿用当前服务配置，还是需要按资料类型单独配置？
- 前端回答卡片是否只展示“已使用资料”摘要，还是允许展开查看短 evidence 摘要？
- 当简历/JD 加载失败但知识库可用时，回答应直接失败，还是 degraded 继续回答并显式提示？
