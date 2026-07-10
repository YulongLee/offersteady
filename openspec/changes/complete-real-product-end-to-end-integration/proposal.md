## Why

当前 OfferSteady 虽然已经分阶段接入了登录、上传、文档处理、检索、聊天、截图和语音能力，但前端主工作流仍大量依赖 fixture / mock，后端也仍混用 in-memory 与 synthetic 适配器，导致“页面能演示”不等于“产品真实可用”。在进入下一阶段开发前，需要完成一轮面向真实业务链路的全产品联调，明确哪些链路已经闭环、哪些问题仍阻塞上线，并把结果沉淀为可执行的 Bug List 与 TODO List。

## What Changes

- 新增一条“真实全链路产品联调”变更，覆盖登录、Resume 上传、JD 上传、Knowledge 上传、OSS、MinerU、Embedding、pgvector、Retrieval、Interview Session、Chat、Screenshot、Speech、History。
- 要求联调过程中 Frontend 不再继续使用 fixture / mock 数据作为主数据源，所有核心页面状态必须来自真实后端 API 或真实联调事实源。
- 对现有全链路中的 synthetic、placeholder、in-memory 依赖进行梳理，并把会影响真实联调结论的缺口显式纳入 Bug List 和 TODO List。
- 统一要求所有 AI 与存储链路使用真实 provider：文件走 OSS，解析走 MinerU，向量与检索走 Embedding + pgvector，问答/视觉/语音走 DashScope。
- 生成一份完整的 Integration Report，同时附带结构化 Bug List 和 TODO List，作为后续 apply 与修复优先级依据。

## Capabilities

### New Capabilities
- `real-product-end-to-end-integration`: 提供覆盖 OfferSteady 全业务主路径的真实环境联调能力，要求前端禁用主流程 mock，并输出 Integration Report。
- `integration-defect-triage`: 提供联调结果归档能力，输出结构化 Bug List 与 TODO List，用于区分已阻塞问题、已知缺口和后续修复优先级。

### Modified Capabilities

- None.

## Impact

- Affected frontend areas: `apps/web` 运行时数据源切换、adapter 实现、页面状态装载、联调模式约束
- Affected backend areas: `apps/backend/app/modules`, `apps/backend/app/services`, `apps/backend/app/deps`, `apps/backend/tests`
- Affected docs: `docs/architecture.md`, `docs/engineering-foundation.md`, `docs/environment-variables.md`, `apps/backend/README.md`, 新增联调报告与缺陷归档说明
- Affected infrastructure: Aliyun OSS, MinerU, DashScope Chat / Vision / Realtime ASR / Embedding / Rerank, PostgreSQL, pgvector
- Affected operations: 联调环境准备、真实 API 费用控制、脱敏样本管理、报告输出、缺陷清单维护
