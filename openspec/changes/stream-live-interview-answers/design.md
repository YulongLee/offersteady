## Context

当前 live-answer 链路已经能调用真实模型，并在响应中返回 `chunks`。但这些 chunks 是在后端完成整次生成后一次性返回给前端，用户仍然要等完整模型调用结束才能看到主要回答。这不符合面试现场“边生成边看”的使用场景。

这次变更只处理实时面试页手动问题 / 快答的回答流式输出。它不重做页面布局，不修改 prompt 策略，不改截图回答和语音链路。

## Goals / Non-Goals

**Goals:**

- 用户点击快答后尽快看到首个回答片段
- 后端提供真正增量的 live-answer streaming event contract
- 前端按事件持续更新当前回答正文
- 支持流式过程中的取消、失败、历史查看和重试
- 保持现有实时面试页布局不变

**Non-Goals:**

- 不更换模型供应商
- 不重做 prompt 或 RAG 策略
- 不实现截图回答流式化
- 不实现实时语音答案流式化
- 不引入新的客户端密钥或浏览器直连模型

## Decisions

### Decision 1: Use SSE for first-phase answer streaming

优先采用 Server-Sent Events 作为 Web 端实时回答流式协议。前端提交问题后，后端返回 `text/event-stream`，按顺序推送 task-started、chunk、completed、failed、cancelled 等事件。

Rationale:

- 当前是后端单向向浏览器推送文本，SSE 足够贴合
- 浏览器支持轻量，不需要引入完整 WebSocket 会话管理
- 比轮询更低延迟，也更符合用户“立刻看到字出来”的期待
- 后续截图回答或语音触发回答可以复用同一事件格式

Alternatives considered:

- WebSocket：适合双向长期连接，但本次只需要单次回答增量输出，会增加连接与鉴权复杂度
- Polling task chunks：实现简单，但延迟和请求频率都会影响面试现场体验
- Keep existing response chunks：实现最少，但不能解决用户感知慢的问题

### Decision 2: Keep task state authoritative on the backend

每次流式回答仍创建后端 task。SSE 只是传输通道，最终 completed / failed / cancelled 状态必须落到后端 repository 和会话历史。

Rationale:

- 刷新页面、查看历史、取消回答和复盘都需要服务端状态一致
- 前端不能只靠本地流式文本作为最终事实源

### Decision 3: Event payloads are small and render-oriented

事件建议包含：

- `task-started`: task id、question、session id、initial status
- `chunk`: task id、sequence、text、isFinal
- `completed`: final task snapshot、answerText、usage summary if safe
- `failed`: task id、safe error code/message、partial text if available
- `cancelled`: task id、final cancelled status

事件不得包含 API Key、完整 Prompt、原始简历/JD/知识库正文或上游供应商完整原始响应。

### Decision 4: Frontend adapter owns stream consumption details

React 页面不直接处理 SSE 解析细节。`backend-adapter` 或相邻客户端模块负责：

- 发起 streaming request
- 解析事件
- 将事件映射为 `InterviewQuestion` / `AnswerTaskSnapshot` 更新
- 暴露取消或 abort 能力

Rationale:

- 页面组件保持专注于渲染和交互
- 后续如果从 SSE 换成 fetch readable stream 或 WebSocket，UI 不需要重写

### Decision 5: Cancellation is best effort but UI must stop updating immediately

用户点击终止回答后，前端立即停止消费该 task 的可见 chunk，并调用后端 cancel endpoint。后端取消成功后将 task 标记为 cancelled；如果供应商晚到 chunk，系统必须忽略或隔离。

Rationale:

- 面试现场用户点击停止通常是因为这个回答已经不需要，继续追加文字会很干扰
- 供应商层未必支持即时中断，但 OfferSteady task 状态必须权威

## Risks / Trade-offs

- [Risk] SSE over some proxies buffers output and降低实时性 -> Mitigation: set `text/event-stream`, no-cache, and flush small events from the backend; document local Nginx/proxy requirements when deployment config exists
- [Risk] Token usage may only be known after completion -> Mitigation: stream chunks first, emit final usage in completed event
- [Risk] User navigates history while latest stream updates -> Mitigation: keep updates bound by task id and show latest-answer notice without stealing current history view
- [Risk] Cancellation races with provider chunks -> Mitigation: frontend aborts consumption immediately; backend rejects late chunks from visible completed answer
- [Risk] Streaming tests become flaky -> Mitigation: use deterministic fake chunk generators and event parser unit tests, plus one integration test for ordered events

## Migration Plan

1. Define stream event schema in backend and frontend test fixtures.
2. Add live-answer streaming endpoint or streaming mode to the existing question endpoint.
3. Teach Chat gateway/service to yield chunks as they arrive when supported, while retaining fallback chunking for deterministic tests.
4. Add frontend adapter stream consumption and state updates.
5. Update answer workspace tests for first chunk, append, completion, failure, cancellation and history viewing.
6. Keep existing non-streaming task response for compatibility until the frontend streaming path is verified.

Rollback strategy:

- Keep the existing non-streaming `/api/v1/live-answer/questions` response as a fallback during rollout.
- If streaming fails in development, the UI should show failed state and allow retry, not silently claim completion.

## Open Questions

- Should the first implementation use a separate endpoint such as `/api/v1/live-answer/questions/stream`, or content negotiation on the existing endpoint?
- Should real Qwen streaming be enabled immediately, or should the first backend implementation stream deterministic chunks from the completed response while the provider streaming adapter is added next?
