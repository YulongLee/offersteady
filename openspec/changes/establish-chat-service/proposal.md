## Why

当前系统已经有统一 Document / Processing / Retrieval / Session 基础能力，但还没有真正把“用户问题”转成“实时可读的 AI 回答”的生成服务层。现在需要建立独立 Chat Service，把 Prompt、LLM 调用、流式输出、会话上下文、聊天记录和 token 使用统一收敛起来，作为面试实时问答的正式后端主线。

## What Changes

- 新增统一 Chat Service，负责从用户问题和 Interview Session 生成 AI 面试回答。
- 建立 Chat API，接收用户问题、会话上下文和可选控制参数，并返回流式或结构化回答结果。
- 建立 Prompt Builder、Prompt Template 和 Prompt 配置边界，统一拼接 Session、Resume、JD 和 Retrieval Context。
- 建立可替换 LLM Gateway，第一版以 Qwen Chat API 作为默认目标，但保持后续可切换不同模型。
- 建立 Streaming Response 能力，支持实时输出回答增量，同时与前端原型的实时回答区交互语义保持一致。
- 建立 Conversation History / Conversation Storage 能力，把问题、AI 建议、状态和 token 使用按会话归档。
- 建立 Chat 日志、错误重试和用量记录边界，但不扩展到 Screenshot 或 Speech 流程。

## Capabilities

### New Capabilities
- `chat-service`: 定义统一 Prompt 构建、LLM 调用、流式回答、会话级聊天记录和 token 使用能力

### Modified Capabilities
- None.

## Impact

- Affected code: `apps/backend` 的 live-answer / answer-generation / streaming / session context / retrieval consumption / logging 边界
- APIs: 新增 Chat API、Streaming 输出契约、Conversation History 查询和 Chat 控制接口
- AI assets: 新增 Prompt Template、Prompt Builder 约定、LLM Gateway 和后续 `ai/prompts/`、`ai/evals/` 的扩展入口
- Dependencies: Session Service、Knowledge Retrieval Service、LLM provider adapter、token usage records、conversation storage
- Product behavior: 不改变当前前端原型结构，只为实时问答区域提供正式后端能力
