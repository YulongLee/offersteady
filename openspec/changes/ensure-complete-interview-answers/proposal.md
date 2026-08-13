## Why

实时面试回答当前忽略模型流式响应中的结束原因，并对简单回答和详细回答统一使用较小的输出预算。模型因长度上限停止时，后端仍会把已有片段标记为完成，用户因此看到半句话、未闭合列表或未完成的详细回答。

## What Changes

- 保留模型流式结束原因，区分正常完成与长度截断。
- 为简单回答和详细回答设置各自的输出预算。
- 简单回答或详细回答因长度截断、代码围栏未闭合或明显停在未完成标点时，自动发起有界续写。
- 续写只追加缺失部分，并对相邻片段做重叠去重；已展示内容不得被清空或缩短。
- 只有简单回答和详细回答都完整时，任务才可标记 `completed`；续写耗尽仍不完整时保留部分内容并标记失败。
- 增加隐私安全的完成原因与续写次数日志，不记录问题、回答、Prompt 或资料正文。

## Capabilities

### New Capabilities

- `complete-interview-answer-generation`: 定义两阶段实时回答的完成判断、自动续写、去重、失败语义和观测要求。

### Modified Capabilities

- `live-answer-streaming`: 流式回答在自动续写期间保持同一任务和连续可见正文，且不得把截断内容报告为完成。

## Impact

- Backend: `apps/backend/app/ports/chat.py`, `apps/backend/app/services/chat_service.py`, chat settings and tests.
- AI prompts/evals: add a continuation prompt and synthetic completion eval cases.
- API compatibility: existing SSE event names remain valid; chunks continue to be ordered under the same task.
- Privacy: no raw provider payload, transcript, answer, personal material, or Prompt is added to diagnostics.
