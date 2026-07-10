## Context

当前产品原型已经支持创建面试、确认资料、进入实时面试页面，并在右侧回答区提供“回答问题”和“截图回答”操作。近期变更已经要求产品运行时统一读取 Backend API，且后端已经存在 Live Answer / Chat Service 的接口与测试基础。

现状问题是：实时面试页的手动输入问题仍在前端直接构造 `InterviewQuestion` 与 `AnswerTaskSnapshot`，并使用本地状态模拟“正在整理回答结构”。这会绕过后端 Chat Service、Retrieval、Prompt Builder、LLM Gateway、Conversation Storage 和 Token Usage，导致真实产品链路没有闭环。

本变更只处理“用户在实时面试页手动输入问题并点击回答问题”的路径。它不改变页面视觉结构，不扩大到截图、语音、本地桌面端采集或支付模块。

## Goals / Non-Goals

**Goals:**

- 用户进入面试页后，可以在手动输入框输入问题并调用当前对话模型生成回答。
- 前端通过 adapter 调用后端 Live Answer API，不再本地合成手动回答。
- 回答状态、回答内容、取消结果、失败结果和历史记录以后端为准。
- Chat Service 使用 Interview Session 绑定的 Resume、JD、Knowledge 配置进行检索增强，前端不拼接 Prompt。
- 保持现有产品原型布局和交互位置不变。

**Non-Goals:**

- 不实现截图回答链路改造。
- 不实现实时语音识别或本地端收音检查。
- 不新增模型供应商。
- 不修改会员、积分价格、兑换码或支付逻辑。
- 不重做实时面试页面 UI。

## Decisions

### Decision 1: 复用 Live Answer API 作为手动问题入口

手动输入问题通过 `POST /api/v1/live-answer/questions` 提交，参数包含当前 `sessionId`、`question`、`stream` 和认证信息。

Rationale: 后端 Chat Service 已经以 Live Answer 为产品语义承载问答、检索、Prompt、LLM、记录和用量统计。复用该入口可以避免再创建一套平行 Chat API。

Alternatives considered:

- 新增 `/api/v1/chat`：接口更通用，但会让实时面试回答和聊天记录归属变得重复。
- 前端直接调用模型：会暴露密钥，并绕过会话、检索和审计边界。

### Decision 2: 前端只负责提交问题和渲染状态

前端 adapter 新增手动回答提交能力，将后端返回的 task / chunks / answerText 映射为现有回答区可渲染的状态。前端不得再本地构造最终回答内容，也不得本地拼接 Prompt 或检索上下文。

Rationale: 产品当前已经要求 Frontend 不继续依赖 syntheticState。回答的权威状态必须来自后端，否则刷新、复盘和多端同步都会失真。

Alternatives considered:

- 前端先乐观创建完整回答：体验快，但容易出现本地成功、后端失败的假状态。
- 前端保留本地假回答作为兜底：会继续掩盖真实链路问题，不符合全链路联调目标。

### Decision 3: 当前阶段接受“请求返回完整 task”，保留流式扩展边界

如果后端当前实现以一次请求返回 completed task 和 chunks，前端先按该结果刷新回答区；后续真正 SSE / WebSocket 流式可在 adapter 内扩展，不改变页面组件调用方式。

Rationale: 先让真实模型调用闭环，比一次性改完整流式传输更稳。adapter 边界可以保护 UI 不被传输协议牵着改。

Alternatives considered:

- 本次直接改成 SSE：更接近最终体验，但会扩大测试范围，并可能影响现有页面稳定性。

### Decision 4: 取消回答继续使用现有 cancel endpoint

若回答任务处于 queued / generating / streaming 状态，用户点击“终止回答”继续调用现有 `/api/v1/live-answer/tasks/{taskId}/cancel`。取消后页面状态以后端返回为准。

Rationale: 终止回答是回答任务生命周期的一部分，应由后端保证状态一致性和记录。

## Risks / Trade-offs

- [Risk] 后端当前返回较慢，用户点击后页面短时间无反馈 → Mitigation: 前端在请求发起后展示“正在调用模型/正在生成回答”的 pending 状态，但最终内容以后端为准。
- [Risk] 后端 Chat Service、Retrieval 或模型配置失败导致用户看不到回答 → Mitigation: 页面显示明确失败信息，保留问题草稿或允许重试，不生成假成功回答。
- [Risk] 流式输出和一次性返回在 UI 状态上不一致 → Mitigation: adapter 输出统一的 answer task 形态，后续只替换传输实现。
- [Risk] 积分/用量在前端和后端同时扣减造成不一致 → Mitigation: 手动问题回答的权威结算以后端返回和后端聚合状态为准，前端不再把本地扣点作为成功依据。

## Migration Plan

1. 为前端 adapter 增加手动问题提交方法，调用现有 Live Answer API。
2. 将实时面试页 `submitManual` 从本地构造回答改为异步调用 adapter。
3. 保留当前回答区组件结构，只替换状态来源。
4. 更新前端测试，覆盖成功、失败、重复点击、取消和刷新历史。
5. 运行 OpenSpec 校验、前端测试、必要的后端契约测试。

Rollback strategy: 如果真实调用链路出现阻塞，可回滚本变更代码，不改变已存在后端 Live Answer API；不得恢复为用户不可见的假成功状态，应显示真实错误。

## Open Questions

- 后续是否需要将手动问题回答改为真正 SSE / WebSocket 流式输出？本变更先保留边界，不强制实现。
- 积分结算是否在 Chat Service 内完成，还是由后续 Billing Service 统一处理？本变更只要求前端不再本地伪造权威结算。
