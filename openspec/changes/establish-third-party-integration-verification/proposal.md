## Why

当前系统已经拆分出 OSS、文档解析、Embedding、检索、聊天、视觉和实时语音等独立边界，但这些边界大多仍停留在架构预留、模拟适配器或局部单测层。进入 MVP 联调前，需要一套独立于业务功能的真实第三方集成验收能力，持续验证所有外部服务、数据库和向量能力是否真的可用，并给出可复跑的集成报告。

## What Changes

- 新增一条生产级第三方集成验证能力，覆盖 OSS、MinerU、Qwen Chat、Qwen Vision、Embedding、Rerank、Realtime ASR、PostgreSQL 和 pgvector。
- 为每个第三方集成定义统一的验证输入、执行日志、结果状态和失败信息，要求测试使用真实 API 和真实基础设施连接。
- 增加可重复执行的 Integration Report 产物，用于汇总每个集成项的环境、耗时、关键指标和最终结论。
- 约束验证能力与现有业务服务解耦，不改变已批准的 Web 原型页面、业务交互和核心接口行为。
- 为后续 apply 阶段预留统一执行入口、环境变量矩阵、日志规范和失败重试策略。

## Capabilities

### New Capabilities
- `third-party-integration-verification`: 提供统一的第三方服务连通性与真实调用验收能力，并输出可重复执行的集成报告。

### Modified Capabilities

- None.

## Impact

- Affected docs: `docs/engineering-foundation.md`, `docs/architecture.md`, `apps/backend/README.md`
- Affected backend areas: `apps/backend/app/adapters`, `apps/backend/app/platform`, `apps/backend/app/services`, `apps/backend/tests` 或独立 `tests/integration`
- Affected runtime dependencies: Aliyun OSS, MinerU, Qwen-compatible chat/vision/realtime providers, embedding / rerank providers, PostgreSQL, pgvector
- Affected operations: environment variable management, provider credential setup, repeatable verification execution, report and log retention
