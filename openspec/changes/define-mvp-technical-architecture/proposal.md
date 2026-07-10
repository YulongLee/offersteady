## Why

OfferSteady 已经有多条围绕 Web、桌面伴随程序、实时面试、资料库和计费的产品变更，但缺少一份面向 MVP 的统一技术架构说明，导致后续实现容易在模块边界、数据流、隐私约束和可替换依赖上各自演化。现在补齐这份 Architecture Design，可以在不提前锁死技术栈的前提下，先统一系统分层、关键接口和演进边界。

## What Changes

- 新增一份面向 MVP 的整体技术架构设计，覆盖 Web 应用、桌面伴随程序、应用 API、AI 编排、资料处理、计费与会话数据管理之间的关系。
- 明确核心运行链路，包括资料导入、实时面试、截图问答、跨端会话同步、积分计费与兑换的系统边界和数据流。
- 定义 MVP 阶段的基础模块划分、接口契约、状态归属、数据存储策略、安全边界和可观测性要求。
- 记录非目标与延后事项，避免在原型阶段过早引入生产级多云、多活、复杂工作流引擎或不可替换的供应商耦合。
- 为后续实现变更提供统一参考，说明哪些能力应放在 `apps/*`、`packages/*`、`ai/*` 与 `docs/*` 中维护。

## Capabilities

### New Capabilities
- `mvp-technical-architecture`: 定义 MVP 整体技术架构文档必须覆盖的系统组件、集成边界、数据处理原则和演进约束

### Modified Capabilities
- None

## Impact

- Affected docs: `docs/architecture.md`、相关决策文档、后续架构说明资料
- Affected systems: `apps/web`、`apps/api`、未来 `apps/desktop`、`packages/protocol`、`ai/prompts`、`ai/evals`
- Affected decisions: 资料处理链路、实时音频桥接、跨端会话同步、积分计费与兑换、隐私与删除策略、供应商适配器边界
