## Why

当前实时面试页的快答虽然已经调用真实模型，但页面通常要等后端拿到完整回答后才显示主要内容。面试现场对延迟非常敏感，用户需要在模型生成过程中尽快看到可读片段，否则会感觉“卡住了”，也会影响临场使用信心。

## What Changes

- 将实时面试页 AI 回答改为真正的流式输出：用户点击快答后，右侧回答区应尽快出现首段内容，并随着模型生成持续追加。
- 后端 live-answer 支持增量传输协议，优先采用 Server-Sent Events（SSE）或等价的可取消、可恢复状态更新机制。
- 前端 adapter 支持读取流式事件，将 ordered chunks 映射为当前回答正文、生成状态、完成状态和失败状态。
- 保留现有页面布局：左侧实时对话、右侧回答、底部快答 / 截屏回答位置不变。
- 终止回答必须能停止前端继续消费流，并调用后端取消任务；后端需要拒绝或忽略取消后的迟到 chunk。
- 失败时保留已生成的部分内容和原问题，显示明确可重试错误，不伪造完成状态。
- 本变更不修改模型供应商、Prompt 策略、资料选择流程、截图回答、实时语音、登录、支付和积分规则。

## Capabilities

### New Capabilities

- `live-answer-streaming`: 定义实时面试回答的增量传输、前端消费、取消、失败和完成信号。

### Modified Capabilities

- `resizable-live-interview-workspace`: 实时回答区在生成中必须持续展示模型已返回正文片段，且响应式切换、拖拽分栏、历史查看和终止回答不得丢失当前流式状态。

## Impact

- Affected backend areas: `apps/backend/app/modules/live_answer.py`, `apps/backend/app/services/chat_service.py`, `apps/backend/app/ports/chat.py`, live-answer schemas/tests
- Affected frontend areas: `apps/web/src/backend-adapter.ts`, `apps/web/src/App.tsx`, `apps/web/src/AnswerWorkspace.tsx`, 实时页状态与回归测试
- Affected protocol/API: 新增或扩展 live-answer streaming endpoint / event contract，例如 task-started、chunk、completed、failed、cancelled
- Affected UX: 快答点击后应快速看到首个片段，回答区保持“正在生成”状态直到完成或失败
- Privacy impact: 流式事件只传递当前回答任务所需的脱敏状态与模型输出片段，不暴露模型密钥、完整 Prompt 或额外个人资料原文
