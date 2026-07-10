## Context

当前 OfferSteady 已经具备文档上传、文档处理、向量化和知识检索的基础能力，也已经在原型和既有 Specs 中明确了“继续面试”“准备页确认本场资料”“恢复实时工作台”“结束面试”和“重新开始”的产品语义。但服务端还没有一个统一的 Interview Session Service 去承载这些状态。

现在的空缺主要体现在三点：

- 会话相关状态仍停留在占位模块，无法成为 Retrieval、Answer、Screenshot、Desktop Bridge 和 Billing 的统一上下文来源。
- 资料选择、模型配置、Prompt 配置、检索配置、多轮上下文和用量统计还没有沉淀为会话快照，后续很容易分散到多个服务内部。
- 当前产品已经明确“前端原型交互不能被改写”，所以后端需要补足权威会话状态，而不是通过新增页面流程来弥补数据模型缺口。

因此，这次设计需要在不改动原型交互的前提下，建立一个统一的会话聚合层，让后续 Chat Service 只消费会话上下文，而不是自己兼任会话管理。

## Goals / Non-Goals

**Goals:**

- 建立统一 Interview Session Service，作为一次面试的权威业务上下文
- 支持会话生命周期、资料绑定、配置快照、上下文管理、用量统计、恢复与重新开始
- 为 Retrieval、Chat、Screenshot、Desktop Bridge 和 Billing 提供统一会话主键与读取入口
- 保持产品原型中的继续面试、准备页、实时页和结束逻辑不变
- 保持外部模型、检索、流式输出和桌面桥接适配器可替换

**Non-Goals:**

- 不实现 Chat Service
- 不实现 Streaming
- 不实现 LLM 调用
- 不改变前端原型页面结构、按钮语义或流程顺序
- 不在本次变更里实现桌面设备绑定、截图分析或计费结算逻辑本身

## Decisions

### 1. Use one session aggregate as the authoritative state owner

Interview Session Service 将以一个“会话聚合”承载：

- session identity
- lifecycle state
- bound materials
- configuration snapshots
- conversation context
- usage statistics

下游服务只引用 session id 和读取会话上下文，不再把“本场面试是什么”保存在自己内部。

原因：

- 当前多个能力都围绕同一场面试协作，必须有单一权威状态
- 能避免 Retrieval、Answer、Desktop Bridge 各自维护一套 session-like 结构
- 与已有架构文档中的“server authoritative session state”方向一致

备选方案：

- 继续让每个服务维护自己的会话上下文：实现快，但后续恢复、计费和审计会非常混乱

### 2. Model session lifecycle explicitly around the approved prototype

第一版会话状态采用显式生命周期，而不是只有“是否进行中”布尔值。建议的主状态包括：

- `preparing`
- `live`
- `ended`
- `archived`（可选后续态，用于长期整理或运营归档）

其中“继续面试”的目标由服务端根据会话状态决定：

- `preparing` → 恢复准备页
- `live` → 恢复实时页
- `ended` → 进入历史会话查看或触发重新开始

原因：

- 原型已经要求继续面试由服务端状态驱动
- 会话恢复和重新开始需要与“已结束”明确区分
- 比隐式状态推断更适合后续桌面桥接和异步任务协作

备选方案：

- 用零散字段临时推断：如 `started_at != null`、`ended_at == null`；这种方式简单但很容易出现歧义

### 3. Bind materials by session snapshot, not by mutable account defaults

会话不直接“引用用户当前资料库默认值”，而是在用户确认本场资料时生成一份 session-scoped binding snapshot，记录：

- selected resume document id（可空）
- selected JD document id（可空）
- selected knowledge document ids（可多个）
- selection revision / confirmed timestamp
- selected source display metadata snapshot

原因：

- 产品已经明确“本场资料可为空，且不得静默继承其他资料”
- 删除或失效后的资料也需要保留历史引用痕迹
- Retrieval 和后续 Chat 需要知道“本场实际允许用哪些资料”

备选方案：

- 每次实时读取账号当前最新资料：实现更省事，但会破坏历史一致性

### 4. Snapshot model, prompt, and retrieval settings at session scope

Session Service 为每场会话保存一份配置快照，而不是仅依赖当前运行时默认值。快照至少包含：

- model config reference
- prompt config reference
- retrieval config reference
- optional revision / version fields

原因：

- 同一场会话在后续恢复时应保持上下文一致
- 便于将来分析“哪套配置带来了什么效果和消耗”
- 避免全局配置变化后影响历史会话复现和调试

备选方案：

- 不保存快照，只在调用时读取全局设置：简单，但会让历史会话不可复现

### 5. Keep conversation context as structured session records, not raw chat text blobs

Conversation Context 第一版不以“单段拼接文本”保存，而使用结构化记录：

- context entry id
- session id
- role / source kind
- content summary or normalized text
- relation to answer task / screenshot task / transcript span
- visibility / persistence boundary
- timestamp / ordering cursor

原因：

- 后续既要支持实时页恢复，也要支持 Retrieval、Chat、Review 使用
- 有利于最小化保存和按类型删除
- 可区分 interviewer / me / manual question / AI advice / system event

备选方案：

- 仅维护一段会话 transcript：实现快，但对恢复、过滤和审计都不够用

### 6. Represent restart as “create a new session from an old seed”

“重新开始面试”不修改已结束会话，而是从既有会话复制可复用信息，创建一场新的 session seed。可复用信息包括：

- approved material scope
- config snapshots
- optional template metadata（如 title / target company / interview type）

不会默认复制的内容包括：

- active answer task state
- streaming state
- transient device connection state
- stale in-flight interruptions

原因：

- 历史会话应保持不可变，便于审计与复盘
- 重启本质上是“新的一场”，不是把旧会话重新打开
- 有利于避免历史转录和新一场面试混杂

备选方案：

- 把 ended session 改回 live：实现更简单，但会破坏历史语义

### 7. Track token usage at session scope but keep billing separate

Session Service 保存结构化 token usage ledger 和 totals，但不直接结算会员或积分。第一版只定义：

- usage event shape
- totals update rules
- query/read API

Billing 仍可在后续单独读取这些数据做结算或对账。

原因：

- 使用统计与会话天然强相关
- 计费策略会变化，不应把 billing policy 硬编码在 session 模块
- 能满足你要求的“为 Chat Service 提供统一上下文”，同时给后续商业系统留接口

备选方案：

- 把 token 统计完全放在 billing：会让 chat / review / audit 难以单独读取会话成本

### 8. Keep session APIs orchestration-friendly and provider-agnostic

Session API 主要提供：

- create session
- get session detail
- list recoverable / historical sessions
- confirm material bindings
- update or read config snapshot
- append context entry
- get context window
- record usage
- end session
- restart session

这些 API 只暴露产品级语义，不暴露底层 LLM、stream、desktop transport 或 provider-specific 参数。

原因：

- 保持会话层稳定，后续供应商变化不影响会话契约
- 与当前架构要求的“adapter replaceable”一致

备选方案：

- 在 session API 中直接暴露模型请求参数和流式细节：短期方便，但会把 orchestration 与 provider 耦合起来

## Risks / Trade-offs

- [Risk] 会话模型过大，首版实现显得复杂 → Mitigation: 将 lifecycle、materials、configs、context、usage 拆成清晰子模型，但由一个 service 统一编排
- [Risk] 资料绑定与文档删除后的历史一致性容易混淆 → Mitigation: 使用绑定快照并保留 “inactive / deleted / unavailable” 可见状态
- [Risk] 多轮上下文若全部持久化，可能增加敏感数据面 → Mitigation: 默认只保存必要结构化记录，原始音频仍不长期保存，并为不同 context type 预留删除边界
- [Risk] restart 语义若不清晰，可能与 continue 混淆 → Mitigation: continue 只恢复同一未结束会话；restart 总是创建新会话
- [Risk] token usage 与 billing 后续对不上 → Mitigation: session 只记录事实性 usage ledger，不在本次变更中承担计费规则

## Migration Plan

1. 在 OpenSpec 中定义 Interview Session Service 的能力边界、生命周期和恢复语义
2. 在 `apps/backend` 中把当前占位 `session` 模块替换为真实的 session domain 边界
3. 建立 Session repository、schemas、service、API 和与 document / retrieval 的引用关系
4. 让后续 Chat Service、Desktop Bridge、Screenshot Service 统一基于 session id 读取上下文
5. 在不改变前端交互的前提下，把已有“继续面试 / 开始面试 / 结束 / 重新开始”的页面动作逐步接入正式 API

回滚策略：

- 如果实现阶段出现问题，可临时保留当前 placeholder session router，同时不影响 document / retrieval 已有能力
- 因为本次只建立会话服务边界，不直接改 Chat/Streaming provider，所以回滚范围可限制在 `session` 模块内部

## Open Questions

- 第一版是否需要区分 `paused` / `recoverable-live` 与 `live`，还是先统一由 `live` + recoverability metadata 表达？
- Conversation Context 第一版是否需要保存完整 AI 建议正文，还是只保存摘要与引用关系，把正文交给后续 Answer Service 管理？
- Session usage ledger 是否从第一版开始区分 prompt / completion / embedding / retrieval 四类成本，还是先只记录总 token？
- 重新开始面试时，是否需要允许用户选择“复制历史资料选择但清空历史上下文”，作为固定默认行为？
