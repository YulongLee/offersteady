## Context

OfferSteady 当前已经具备较完整的模块边界：认证、文档上传、文档处理、检索、会话、聊天、截图回答和实时语音都已存在独立 API 与 service 层；同时 OSS、MinerU、DashScope、PostgreSQL 和 pgvector 的第三方连通性也已经分别验证过。但真实产品链路还没有完全成立，原因主要有三类：

- 前端主工作流仍大量经由 `fixtureAdapter` 和 fallback adapter 装载页面状态，导致页面可演示但不代表真实产品状态。
- 后端仍混用 `InMemory*Repository`、`Synthetic*Adapter` 和 placeholder provider，导致部分接口虽然存在，但事实源不是持久化存储或真实 provider。
- 现有联调报告只覆盖“是否通过”，尚未结构化输出 Bug List 与 TODO List，因此无法把联调结果直接变成后续修复计划。

这次变更的目标不是新增产品功能，而是把当前系统推进到“真实联调可验收”的状态：前端核心状态不再依赖 mock，核心链路全部走真实 provider，并把问题归档成标准化产物。

## Goals / Non-Goals

**Goals:**

- 建立一条真实全链路联调线，覆盖登录、上传、解析、向量化、检索、问答、截图、语音和历史查询。
- 禁止前端核心页面在联调模式下使用 fixture / mock 作为权威数据源。
- 逐步替换阻塞真实联调判断的 `Synthetic*`、`InMemory*`、placeholder 适配器。
- 为每次联调输出 Integration Report、Bug List、TODO List 三类结果。
- 保持当前批准的产品原型页面结构、交互顺序和主要文案组织不变。

**Non-Goals:**

- 不在本变更中新增新的商业页面、会员功能或后台管理系统。
- 不重做前端视觉结构，也不重新定义产品交互。
- 不要求一次性把所有内部存储全部生产化；本变更只优先替换会影响真实联调结论的关键路径。
- 不把 Bug 修复全部打包进单次提案；重点是建立真实联调边界与缺陷归档标准。

## Decisions

### 1. 采用“前端 API-only 联调模式”而不是现有 probe-then-fallback 模式

当前 `BackendPreviewInterviewAdapter` 只探测后端是否可达，但实际状态仍回退到 fixture。新的联调模式将要求：

- 前端核心页面状态必须由后端 API 返回
- 若关键接口缺失或返回异常，联调直接失败
- 不允许 silently fallback 到 fixture 数据

选择这个方案的原因是：联调的目标是暴露真实问题，而不是维持演示稳定性。

备选方案：

- 保留 fallback，只在报告里标注：会掩盖联调问题，无法证明真实产品可用。
- 直接删除 fixture 模式：会影响日常原型演示与本地低成本开发，因此只在联调模式禁用。

### 2. 按“阻塞真实联调结论”的优先级替换 synthetic / in-memory 适配器

不是所有 placeholder 都必须同时替换，但以下路径必须优先真实化：

- 前端核心状态读取
- 文档元数据事实源
- 会话、上下文、历史事实源
- 向量写入与检索事实源
- 截图 / 语音 / 聊天的真实 provider 调用

仍可暂缓的项应进入 TODO List，而不是混入“已真实联调通过”结论。

备选方案：

- 一次性全面生产化所有 adapter：范围过大，容易把联调变更变成全面重构。
- 维持现状只跑 provider smoke test：无法证明产品链路成立。

### 3. 用“报告 + 缺陷分级”替代单一通过/失败结论

这次联调输出需要同时包括：

- Integration Report：整体运行事实
- Bug List：阻塞问题、缺陷、契约不一致
- TODO List：已知非阻塞缺口与后续替换项

Bug List 和 TODO List 必须显式区分：

- release blocker
- major risk
- deferred follow-up

这样联调结果才能直接转化成下一轮 apply 的修复清单。

备选方案：

- 只输出 Integration Report：信息不够，无法直接指导修复。
- 把所有问题都塞进 tasks：会混淆“事实发现”和“批准实施”的边界。

### 4. 真实联调继续使用脱敏样本，但不得继续使用 synthetic 业务结果

本变更仍遵守隐私边界：

- Resume / JD / Knowledge / Screenshot / Audio 样本必须是合成或脱敏
- 但业务结果必须来自真实 provider、真实 API、真实后台状态推进

这意味着“样本可以是合成的，结果不可以是硬编码的”。

### 5. 真实联调以 CLI orchestration 为主，前端页面联调为辅

联调主执行器仍优先采用后端 orchestrator / test runner，因为：

- 它更稳定
- 更容易输出结构化报告
- 更容易隔离 provider 问题、前端契约问题和环境问题

前端页面联调则作为补充验收层，验证用户可见状态确实来自真实 API。

## Risks / Trade-offs

- [真实 provider 成本更高] → 使用最小样本、可分步执行、支持单场景重跑。
- [前端去掉 fallback 后更容易失败] → 把失败视为联调价值的一部分，并在 Bug List 中结构化记录。
- [现有 in-memory 实现可能导致“看似通过但不可持久化”] → 报告中明确标注事实源类型，并把持久化缺口列入 Bug List 或 TODO List。
- [真实 AI 输出不稳定] → 以链路闭环、状态推进、最小语义信号作为验收标准，不对自然语言文本做完全固定断言。
- [联调范围过大] → 按登录、文档、检索、聊天、截图、语音、历史分场景执行，并允许独立失败归因。

## Migration Plan

1. 定义新的 capability specs，明确“前端禁用 mock”“真实 provider”“Bug/TODO 输出”的验收边界。
2. 新增联调模式约束，区分原型演示模式与真实联调模式。
3. 替换或隔离阻塞真实联调结论的 fallback / synthetic / in-memory 路径。
4. 执行真实联调，生成 Integration Report、Bug List、TODO List。
5. 基于 Bug List 和 TODO List 决定下一轮 apply 的修复顺序。

若需要回滚，可移除新的联调约束与报告输出，但不应回退已经完成的真实 provider 接入；前端 fixture 模式可继续保留给原型演示使用。

## Open Questions

- 哪些 in-memory repository 需要在本变更中直接替换为 PostgreSQL，哪些只需在报告中标记为 blocker 即可？
- Frontend API-only 联调模式是否需要独立环境变量，例如强制禁止 fallback？
- Bug List 和 TODO List 是否需要固定为仓库内可追踪文件，还是只作为每次运行的 artifacts 输出？
- Realtime Speech 的页面级联调是否要求浏览器真实展示验证，还是以后端 transcript / answer flow 成功为准？
