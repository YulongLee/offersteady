## Context

OfferSteady 当前已经具备一套分层清晰的 MVP 基础工程：前端原型保持既有交互，后端通过 FastAPI 提供统一 API 边界，文档、检索、聊天、截图与实时语音能力通过独立模块和第三方适配器接入。最近的第三方集成验收已经逐步打通了 OSS、MinerU、PostgreSQL、pgvector、Embedding、Chat、Vision、Rerank 和 Realtime ASR，但这些验证主要聚焦在 provider 层和服务层的分段成功。

用户当前需要的是“整条产品链路”的真实环境联调：从注册登录开始，经过 Resume / JD / Knowledge 上传、OSS 存储、Parser、Chunk、Embedding、向量入库、检索、会话管理、回答生成、截图理解、实时语音辅助，到最终会话记录与历史查询，确保整条链路能以真实 API 协同运行，同时不改变已批准的产品原型交互。

## Goals / Non-Goals

**Goals:**

- 建立一套可重复执行的端到端联调流程，覆盖产品主路径与关键 AI 能力。
- 前端在联调模式下切换到真实 API，不再依赖 mock / fixture 输出。
- 统一验证所有文件落 OSS、所有向量落 pgvector、所有 AI 统一走 DashScope。
- 生成可用于验收和回归对比的 Integration Report。
- 在保持原型结构不变的前提下，验证用户流程和后端业务状态是否真实贯通。

**Non-Goals:**

- 不新增新的前端页面、交互步骤或商业功能。
- 不改变当前已批准的产品原型结构、文案顺序和核心操作路径。
- 不在本变更中重构已有业务边界，只补齐联调所需的协调层、验收脚本和联调测试。
- 不把联调逻辑耦合进正式用户请求链路。

## Decisions

### 1. 采用“场景驱动 E2E 联调”而不是只扩展模块单测

这次联调会按真实业务顺序组织成若干 E2E 场景，例如：

- 注册 / 登录 → 创建 Session
- 上传 Resume / JD / Knowledge → OSS → Parser → Chunk → Embedding → pgvector
- 绑定资料 → Retrieval → Chat 回答
- 上传截图 → Vision → Retrieval → Screenshot Answer
- 创建 Realtime Speech 会话 → 实时字幕 → 问题识别 → 回答生成
- 查询 Conversation Storage / Interview History

原因是单独的 provider 验证虽然重要，但不能保证跨模块状态、依赖顺序与前端 API 调用能够协同工作。

备选方案：

- 只保留模块级集成测试：无法验证前端 API 模式、Session 状态推进与跨模块数据交接。
- 只做人手联调：结果不稳定，难以回归和报告归档。

### 2. 前端联调必须保留原型交互，但切换到真实 API 模式

当前 `apps/web` 已经支持 fixture/prototype 与 API 双模式。全链路联调会显式要求：

- 保持当前页面结构和交互顺序
- 在联调模式下切换为真实 API
- 使用联调专用 synthetic / sanitized 数据

这样既能保护原型完整性，又能验证前后端契约是否真实匹配。

### 3. 联调数据全部使用合成或脱敏样本

虽然全部要求真实 API，但联调样本仍必须遵守项目数据边界：

- Resume / JD / Knowledge 使用仓库内或联调脚本生成的脱敏样本
- Screenshot 使用测试图
- Realtime Speech 使用合成或本地 TTS 语音样本

这样既满足真实联调，也避免把真实候选人材料写入日志、测试工件或第三方模型。

### 4. Integration Report 分为“模块通过”与“场景通过”两层

第三方 provider 通过并不等于业务链路通过，因此联调报告需要至少包含两层：

- Provider readiness：第三方底座是否已准备好
- Scenario readiness：完整业务场景是否成功闭环

例如：

- Vision provider 通过
- Screenshot Answer E2E 场景也需要单独标为通过

### 5. Conversation 与历史联调以服务端事实源为准

联调时 Conversation Storage 与 Interview History 的验收不只看前端是否显示，还要核对：

- 服务端是否真实落库 / 持久化到当前实现的事实源
- Session 绑定是否正确
- Usage / answer / transcript / screenshot record 是否能回查

### 6. 失败归因要区分前端契约、业务服务和第三方 provider

端到端联调最容易出现“失败了但不知道是谁的问题”。因此每个场景报告都必须明确归因：

- Frontend request / runtime mode issue
- Backend module orchestration issue
- Provider / infrastructure issue
- Test fixture / environment bootstrap issue

## Risks / Trade-offs

- [真实联调成本更高] → 使用最小样本、可分场景执行、分层报告，减少全量重跑成本。
- [前端切 API 后会暴露大量契约问题] → 联调前先固定 API 版本和环境变量矩阵，报告中明确契约差异。
- [多模块串联后失败点更难定位] → 报告按步骤记录 request id、模块阶段和 provider 事件。
- [真实 AI 输出不稳定] → 验收以“链路成功 + 最低可接受语义信号”判定，不把生成文本完全写死。
- [联调可能触发真实敏感数据上传] → 强制使用脱敏样本目录和联调专用脚本，不默认读取用户本地真实文件。

## Migration Plan

1. 定义 E2E capability spec、联调场景清单和报告结构。
2. 补充联调环境变量、前端 API 运行模式说明和联调样本。
3. 在后端新增端到端联调 runner / tests，串联登录、上传、处理、检索、会话、回答与历史查询。
4. 在联调脚本中接入现有第三方集成验证结果，确保 provider 就绪后再跑场景。
5. 生成最终 Integration Report，并据此确认 MVP 联调 readiness。

若回滚，只需移除联调 runner、E2E 脚本和联调文档，不影响现有原型与业务主线。

## Open Questions

- Conversation Storage / Interview History 当前是内存实现还是已接到持久化事实源，联调验收应如何分层标注？
- Frontend API 模式切换是否需要单独的联调入口命令，避免误用 fixture 模式？
- 全量联调是通过 pytest / CLI 执行，还是需要补一个统一 orchestrator 命令？
- Realtime Speech E2E 场景是否以“服务端收到 transcript 和 answer 触发”为通过标准，还是还要包含前端实时展示验证？
