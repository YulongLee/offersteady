## Why

当前实时面试页的回答区展示了提纲、展开详情、推断说明和来源块，真实使用时信息层级过多，用户反而不容易快速拿到可直接参考的回答内容。同时，回答组织策略有一部分仍体现在前端展示结构里，不利于后续统一在后端 prompt 中持续优化。

## What Changes

- 将实时面试页的回答区改为优先直接展示模型返回的回答正文，减少固定的前端解释层和复杂结构。
- 把“回答策略”“组织方式”“表达风格”等可调整逻辑统一收敛到后端 Prompt Template / Prompt Builder / Chat Service 中维护。
- 前端回答区继续保留必要的状态信息，例如生成中、失败、终止回答、历史翻页和最小化来源提示，但不再强制用固定提纲卡片承载回答。
- 后端回答契约改为以“主回答正文”为第一展示内容，前端不再假设每次回答都需要 `outline + detail + inference` 的复杂组合才能渲染。
- 不修改现有面试进入流程、快答入口、截图回答入口、积分规则、登录流程和页面主布局。

## Capabilities

### New Capabilities

- `backend-prompt-owned-answer-strategy`: 定义回答策略、表达结构和风格控制由后端 Prompt Template / Builder / Chat Service 统一维护，前端不再承载策略结构。

### Modified Capabilities

- `resizable-live-interview-workspace`: 回答区的默认呈现从结构化建议卡片调整为以模型回答正文为主，减少现场阅读负担。

## Impact

- Affected frontend areas: `apps/web/src/AnswerWorkspace.tsx`, `apps/web/src/domain.ts`, `apps/web/src/backend-adapter.ts`, 相关实时页测试
- Affected backend areas: Chat Service、prompt template、prompt builder、live answer response mapping
- Affected AI assets: `ai/prompts/chat-service/` 下的 prompt 内容和版本管理
- Affected user flow: 开始面试 → 手动输入问题/快答 → 回答区直接显示模型正文 → 需要时再查看最小化上下文信息
