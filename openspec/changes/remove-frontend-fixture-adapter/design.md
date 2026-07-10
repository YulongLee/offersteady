## Context

Web 当前仍存在两套页面事实源：`fixtureAdapter` / `syntheticState` 用于原型演示，`BackendPreviewInterviewAdapter` 用于 API 联调但仍保留 fallback。随着认证、文档、会话、截图、语音和全链路联调逐步建立，这种双事实源会让产品页面看起来可用，却无法证明资料、积分、历史和面试状态真的来自当前登录用户的后端数据。

本变更聚焦前端数据源收敛：保持 UI 不变，移除运行时 fixture 读取，让所有页面从 Backend API 装载和更新。测试可以继续使用受控 API mock 或测试数据构造器，但不得让产品运行时代码依赖 `syntheticState`。

## Goals / Non-Goals

**Goals:**

- Web 产品运行时只使用 Backend API 作为页面事实源。
- 首页、资料库、面试记录、用户信息、积分、Screenshot 和 History 都由后端返回真实账号范围内的数据。
- 移除或隔离 `fixtureAdapter`、`syntheticState` 和 fallback-to-fixture 行为。
- 保持现有产品原型页面结构、路由、交互顺序和主要 UI 不变。
- 前端测试从 fixture 状态迁移到 API contract mock 或明确的测试数据构造器。

**Non-Goals:**

- 不修改 AI 能力、RAG、Prompt、模型调用、截图分析或实时语音算法。
- 不重做页面视觉设计，不调整价格、文案或产品流程。
- 不引入新的客户端密钥或把服务端密钥暴露给浏览器。
- 不要求本变更一次性完成所有后端生产级持久化；但前端不得用 fixture 掩盖缺失接口。

## Decisions

### 1. 采用 API-only runtime，移除 `VITE_APP_DATA_SOURCE=fixture`

前端运行时不再根据 `VITE_APP_DATA_SOURCE` 在 fixture 和 API 之间切换。`interviewAppAdapter` 将始终实例化真实 backend adapter，缺失接口通过错误或空状态暴露。

备选方案：保留 fixture 模式作为开发入口。这个方案会继续制造双事实源，容易让真实联调误判为通过，因此不作为产品运行时保留。

### 2. 后端提供前端状态契约，而不是让页面拼接 synthetic state

前端需要一个稳定的状态装载契约，可以是聚合接口，也可以是由 adapter 并发调用多个模块 API 后组装，但数据必须来自 Backend API。建议优先实现 adapter 层聚合，避免为 UI 过早新增过重的后端 BFF；如果多页面重复装载造成明显复杂度，再提升为后端聚合接口。

备选方案：在 UI 组件里直接调用各模块 API。这个方案会把数据装载散落在页面内部，后续难以保证无 mock 和统一错误处理。

### 3. 测试 fixture 与产品 fixture 分离

可以保留测试专用 builders，例如 `buildWebAppStateFixture()` 或 API mock response factory，但不得从产品入口、adapter 或 runtime config 导入 `fixture-adapter.ts`。测试数据必须清楚位于测试辅助路径，不能成为运行时 fallback。

备选方案：彻底删除所有 fixture 文件。这个方案会让大量 UI 回归测试迁移成本变高，也不利于构造复杂边界状态。

### 4. 缺失 API 必须显式失败或展示空状态

如果后端还没有某个页面所需 API，前端需要展示“无法加载/暂无数据”等真实状态，并在测试中记录，不允许回退到 syntheticState。这样能把问题变成 Bug/TODO，而不是隐藏在演示数据后面。

备选方案：先 fallback，后续再删。这个方案与本变更目标冲突。

## Risks / Trade-offs

- [后端接口不完整导致页面短期不可用] → 先梳理页面状态契约，按首页、资料、记录、积分、截图、历史逐项补齐 API 或空状态。
- [测试迁移量较大] → 先建立 API mock/test builder，再批量替换 `syntheticState` imports。
- [移除 fixture 后开发演示成本上升] → 使用本地 backend seed/dev endpoints 或测试账号数据，而不是产品 runtime fixture。
- [页面状态组装复杂] → adapter 层保持统一入口，后续必要时再抽后端聚合接口。
- [真实用户数据风险增加] → API 必须使用 authenticated User ID，并继续使用脱敏样本做自动化测试。

## Migration Plan

1. 盘点所有 `fixtureAdapter`、`syntheticState`、`VITE_APP_DATA_SOURCE` 和 fallback-to-fixture 引用。
2. 定义 Web 页面所需 API 数据契约，并确认现有后端接口是否覆盖。
3. 改造 `app-adapter` 和 `backend-adapter` 为 API-only runtime。
4. 移除 `App.tsx` 中对 `syntheticState` 的默认状态和兜底问题读取。
5. 将页面操作写入真实 API：新建/删除面试、删除截图、终止回答、兑换积分等。
6. 迁移前端测试到 API mock 或测试数据构造器。
7. 更新文档和环境变量说明，删除 fixture 运行模式描述。
8. 运行类型检查、前端测试、后端契约测试和 OpenSpec 校验。

Rollback 策略：如果 API-only 改造导致阻塞，可回滚本变更实现代码，但不应继续扩大 fixture 使用范围；相关缺口应进入全链路联调 Bug List。

## Open Questions

- Web 首页是否采用单个 `/api/v1/web/state` 聚合接口，还是先由 frontend adapter 并发组合现有模块 API？
- 积分页需要哪些最小后端接口覆盖余额、套餐、流水、兑换码和收费说明？
- History 是直接读取 Interview Session / Conversation API，还是需要单独的历史聚合接口？
- 是否需要为开发环境提供受控 seed 命令，用来代替原先的 syntheticState 演示数据？
