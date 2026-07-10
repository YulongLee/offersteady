## Context

`connect-live-manual-chat-to-model` 已经让实时面试页的“回答问题”调用后端 Live Answer / Chat Service。但当前准备页的“开始面试 →”仍只做前端本地状态更新和路由跳转，没有调用后端 Session Start API。

后端 Chat Service 明确要求 Interview Session 状态为 `live` 才能发起回答。如果前端显示已经进入面试，而后端 Session 仍是 `preparing`，用户输入问题后会被后端拒绝，前端再显示通用的“回答生成失败，请稍后重试 / 当前任务未启动，请检查积分或会员权益”，造成错误原因误判。

本修复只同步会话生命周期与错误展示，不改变页面布局、不改变模型链路、不改变积分规则。

## Goals / Non-Goals

**Goals:**

- 点击准备页“开始面试 →”时调用后端 `POST /api/v1/sessions/{sessionId}/start`。
- 后端确认 Session 为 `live` 后再进入实时面试页。
- 启动失败时停留在准备页，并展示后端真实错误。
- 手动回答失败时展示后端真实错误或可理解的错误分类，而不是统一归因到积分/会员。
- 保持现有原型页面结构和手动输入交互不变。

**Non-Goals:**

- 不修改 Chat Service 的状态校验规则。
- 不修改截图回答、实时语音和桌面端收音流程。
- 不实现新的支付、积分或会员逻辑。
- 不新增模型供应商或 Prompt 行为。

## Decisions

### Decision 1: 用后端 Start Session 作为进入 live 页的权威动作

准备页 `startInterview` 应通过 adapter 调用 `POST /api/v1/sessions/{sessionId}/start`。成功后以返回的 Session 状态更新前端面试列表，再跳转到实时面试页。

Rationale: Chat Service 以服务端 Session 状态为准。让前端只本地改 `active` 会制造“假 live”状态，用户看到页面但无法回答。

Alternatives considered:

- 在提交问题前自动补调 start：可以兜底，但会让“进入面试”语义不清晰，且每次回答都要处理启动副作用。
- 放宽后端 Chat Service，允许 preparing 状态回答：会破坏 Session 生命周期边界，也会影响截图和语音的一致性。

### Decision 2: 启动失败不跳转

如果 Start Session API 失败，准备页应保留当前选择和页面位置，并显示明确错误。只有后端确认成功后才进入 live 页面。

Rationale: 失败后进入 live 页只会让后续回答继续失败，用户会陷入“页面看起来可用、实际不可用”的状态。

### Decision 3: 错误提示由具体错误驱动

手动回答失败时，前端应优先展示后端 envelope error message 或 HTTP 错误中的 message。只有无法解析时才使用通用网络/后端不可用提示。积分或会员提示只在明确收到相关计费错误时展示。

Rationale: 当前提示会把 Session 未开始、未登录、模型失败、网络错误都误导成积分问题。错误提示必须帮助用户找到真正下一步。

Alternatives considered:

- 保留统一提示：实现简单，但会继续误导用户。
- 后端统一改错误码：长期可做，但当前前端也应先正确显示已有 message。

## Risks / Trade-offs

- [Risk] 后端启动请求较慢，点击开始后用户重复点击 → Mitigation: 前端增加 starting 状态，按钮展示启动中并禁用重复点击。
- [Risk] API 失败后用户不知道如何继续 → Mitigation: 准备页展示真实错误，并保留资料选择，允许用户重试。
- [Risk] 错误来源较多，文案不稳定 → Mitigation: 建立统一错误提取函数或增强 `normalizeError`，优先解析后端 envelope message。
- [Risk] 历史测试仍假设开始面试只本地跳转 → Mitigation: 更新测试 adapter，覆盖 start 成功和失败。

## Migration Plan

1. 扩展前端 adapter，新增 `startInterviewSession` 方法，调用现有后端 Session Start API。
2. 修改准备页 `startInterview` 为异步流程：pending → backend start → update state → navigate。
3. 修改 Live Answer 错误处理，显示真实错误信息，移除不准确的“检查积分或会员权益”默认说明。
4. 更新测试覆盖：开始面试成功调用后端、开始失败不跳转、手动回答 session 未 live 时展示真实错误。
5. 运行前端测试、类型检查和 OpenSpec 校验。

Rollback strategy: 若启动同步出现回归，可回滚前端 adapter/start flow；后端 Session API 不需要变更。

## Open Questions

- 是否要在用户直接访问 `/app/interviews/:id/live` 时自动检查并恢复后端 live 状态？本修复先聚焦标准“准备页开始面试”路径，直接访问兜底可后续单独处理。
