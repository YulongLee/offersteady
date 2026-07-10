## Why

当前 OfferSteady 已经分别打通了文档上传、文档处理、检索、聊天、截图回答、实时语音和多项第三方基础设施，但这些能力仍然主要停留在模块级联调与分段验收。进入 MVP 真实试运行前，需要建立一条覆盖前端到后端、再到 AI 与数据底座的全链路联调能力，验证所有模块能在真实环境中协同工作，同时保持已批准的产品原型交互不变。

## What Changes

- 新增一条 OfferSteady 全链路真实环境联调能力，覆盖用户注册登录、资料上传、Document Processing Pipeline、Knowledge Retrieval、Interview Session、Chat Service、Screenshot Answer、Realtime Speech、Conversation Storage 与 Interview History。
- 明确 Frontend 联调必须切换到真实 API 数据源，不允许继续依赖 Mock / fixture 结果掩盖后端与 AI 集成问题。
- 约束所有 AI 调用统一使用 DashScope，所有文件统一使用 OSS，所有向量统一使用 pgvector，并要求联调结果以 Integration Report 输出。
- 定义跨模块联调时的环境前置条件、数据边界、运行顺序、失败归因方法和联调报告内容。
- 为后续 apply 阶段预留真实联调脚本、E2E 场景测试、联调数据准备、联调日志与验收报告结构。

## Capabilities

### New Capabilities
- `end-to-end-integration`: 提供覆盖 OfferSteady 全业务链路的真实环境联调能力，并输出可复验的 Integration Report。

### Modified Capabilities

- None.

## Impact

- Affected docs: `docs/architecture.md`, `docs/engineering-foundation.md`, `apps/backend/README.md`, `docs/environment-variables.md`
- Affected frontend areas: `apps/web` 运行时数据源配置、真实 API 联调入口与联调说明
- Affected backend areas: `apps/backend/app/modules`, `apps/backend/app/services`, `apps/backend/tests` 或 `tests/e2e`
- Affected infrastructure: Aliyun OSS, MinerU, DashScope Chat / Vision / Realtime ASR / Embedding / Rerank, PostgreSQL, pgvector
- Affected operations: environment bootstrap, seeded synthetic test data, end-to-end execution commands, integration report generation
