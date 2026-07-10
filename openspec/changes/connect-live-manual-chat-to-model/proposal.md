## Why

当前用户创建面试并确认资料后，已经可以进入实时面试界面，但“回答问题”仍主要停留在前端本地生成状态，用户输入问题后没有稳定接入当前后端 Chat / Live Answer 模型链路。这会让产品看起来进入了真实面试流程，但核心价值“输入问题并获得 AI 回答”没有真正闭环。

现在需要在保持现有产品原型布局和交互不变的前提下，让实时面试页的手动问题输入调用当前对话模型，生成可记录、可复盘、可取消的真实回答。

## What Changes

- 实时面试页面的手动问题输入将调用后端 Live Answer / Chat Service，而不是在前端本地合成回答。
- 用户点击“回答问题”后，系统使用当前 Interview Session、已确认资料范围和当前模型配置生成回答。
- 回答结果、生成状态、失败状态、终止回答和历史记录均以后端返回结果为准。
- 前端保留现有页面结构：左侧实时对话、右侧回答区、底部紧凑问题输入栏，不新增额外页面或改变布局。
- 手动输入问题不负责检查本地端软件收音状态；本地端采集检查仍属于桌面伴随程序和语音链路范围。
- 本变更不修改截图回答、实时语音、支付、积分价格、登录流程和资料库管理。

## Capabilities

### New Capabilities

- `live-manual-chat-model-integration`: 定义实时面试页手动输入问题调用当前 Chat / Live Answer 模型链路的产品行为，包括提交、生成、失败、终止和历史记录。

### Modified Capabilities

- None.

## Impact

- Affected frontend areas: `apps/web/src/App.tsx`, `apps/web/src/backend-adapter.ts`, `apps/web/src/domain.ts`, 相关页面测试
- Affected backend areas: 复用现有 `/api/v1/live-answer/questions`, `/api/v1/live-answer/tasks/{id}`, `/api/v1/live-answer/tasks/{id}/cancel`, `/api/v1/live-answer/sessions/{sessionId}/history`
- Affected product flow: 创建面试 → 确认资料 → 进入面试 → 输入问题 → 调用当前模型生成回答 → 保存历史
- Affected privacy boundary: 前端只传用户问题与会话标识，不在客户端拼接完整 Prompt，不在客户端保存模型密钥
- Dependencies: 依赖既有 Authentication、Interview Session、Retrieval、Chat Service、Qwen / LLM Gateway 配置
