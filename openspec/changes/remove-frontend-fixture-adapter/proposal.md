## Why

当前 Web 原型仍可通过 `fixtureAdapter`、`syntheticState` 或后端 fallback 路径展示页面，导致用户看到的首页、资料库、面试记录、积分、截图和历史信息不一定来自真实后端。现在登录、文档、会话、截图、语音和联调边界已经逐步建立，需要把前端运行时收敛到 Backend API，避免继续用演示数据掩盖真实产品问题。

## What Changes

- **BREAKING**: Web 产品运行时不再支持 `fixture` 数据源作为页面事实源。
- 移除或隔离 `fixtureAdapter`、`syntheticState` 和 probe-then-fallback 行为，所有页面状态统一从 Backend API 装载。
- 首页、资料库、面试记录、用户信息、积分、Screenshot 和 History 均通过真实 API 读取和刷新。
- 前端 API 缺失、后端不可用或响应契约不匹配时，页面必须展示真实错误/空状态，而不是回退到 synthetic 数据。
- 保持已批准的产品原型页面结构、交互顺序和视觉 UI 不变。
- 不修改 AI 能力、模型调用、RAG、Prompt、语音或截图分析逻辑。

## Capabilities

### New Capabilities

- `frontend-api-only-runtime`: 定义 Web 产品运行时必须以 Backend API 作为唯一数据源，禁止读取 fixture / synthetic 页面状态。
- `frontend-backend-state-contract`: 定义前端页面需要的后端聚合状态、页面分区状态和变更操作契约，覆盖首页、资料库、面试记录、用户信息、积分、Screenshot 和 History。

### Modified Capabilities

- None.

## Impact

- Affected frontend: `apps/web/src/app-adapter.ts`, `apps/web/src/backend-adapter.ts`, `apps/web/src/App.tsx`, `apps/web/src/runtime-config.ts`, `apps/web/src/fixture-adapter.ts`, 以及依赖 `syntheticState` 的测试。
- Affected backend: 需要提供前端页面装载所需 API 契约或聚合接口，包括用户、资料、会话、积分、截图和历史记录。
- Affected tests: 前端测试需要从 fixture 状态注入迁移到 API mock/server contract 测试；联调测试需要断言无 fixture fallback。
- Affected docs: `docs/local-web-access.md`, `docs/engineering-foundation.md`, `docs/environment-variables.md` 需要更新前端运行模式说明。
- Privacy impact: 页面展示真实用户资料、截图、会话和历史时必须继续遵守当前最小化保存和账号隔离要求；测试数据仍必须合成或脱敏。
