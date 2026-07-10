## Context

OfferSteady 当前已经形成了分层的 MVP 基础工程：Web 原型保持既有体验，FastAPI 后端负责统一 API、配置、日志和第三方边界，文档处理、检索、聊天、截图回答和实时语音都通过可替换适配器接入。现在缺的不是新的业务功能，而是一条独立的“外部依赖验收线”。

这条验收线必须满足几个约束：

- 不改变产品原型和现有业务流程。
- 必须真实调用第三方服务，而不是使用 fixture、mock 或内存适配器。
- 结果要可重复执行、可定位失败位置、可输出统一报告。
- 凭证只能来自服务端环境变量，日志不得泄露长期密钥、原始简历或原始截图。

## Goals / Non-Goals

**Goals:**

- 建立统一的 Third-party Integration Verification 架构，覆盖对象存储、解析、模型、数据库和向量能力。
- 为每类集成项定义一致的执行契约：输入、步骤、日志、状态、指标、失败原因和最终结论。
- 支持一键或分项执行，生成结构化日志与可读的 Integration Report。
- 保持与业务服务解耦，使其既可作为开发环境自检工具，也可作为上线前验收工具。

**Non-Goals:**

- 不新增任何面向最终用户的业务页面或产品能力。
- 不在本变更中实现 Chat、RAG、截图回答或实时语音的新业务逻辑。
- 不把第三方验证框架直接耦合进线上主请求链路。
- 不引入客户端侧密钥或前端直连第三方服务。

## Decisions

### 1. 采用独立的 verification runner，而不是把验证逻辑散落到各业务模块

将第三方验证实现为独立的 runner / suite 层，由它编排多个 provider-specific verifier。这样可以避免把“环境验收”混入正常业务代码路径，也更适合做全量复跑、分项执行和报告汇总。

备选方案：

- 把验证写成零散的单元测试或路由健康检查：实现快，但无法覆盖真实多步骤调用，也难以生成统一报告。
- 在每个业务服务内部增加 `self_test()`：会污染领域服务边界，并且重复处理日志、报告和执行入口。

### 2. 统一用 step-based result model 表达验证结果

每个集成项都拆成一个或多个步骤，例如 OSS 的 upload / head / download，Qwen Chat 的 request / stream / usage parse，pgvector 的 extension / insert / similarity search。每步都产出统一状态、耗时、摘要和错误信息，最后汇总成 suite 级报告。

这样做的好处是失败定位清晰，且不同供应商能够在同一报告格式下对齐比较。

### 3. 真实调用使用合成或脱敏样本，不复用真实用户材料

虽然要求必须使用真实 API，但输入数据仍应来自仓库内合成样本或运行时生成的安全测试载荷。例如：

- OSS：小型文本或 markdown 样本
- MinerU：合成 PDF / docx 样本
- Chat / Vision / Embedding / Rerank / Realtime ASR：脱敏问题、测试图片、测试音频

这样既满足真实性，又不破坏项目的隐私边界。

### 4. 验证执行入口分为 CLI 主入口和可选 API 触发入口

主入口应为后端侧 CLI / pytest-style integration command，便于本地、CI 和上线前复跑。可选再提供内部受控 API 触发入口，但 API 不作为唯一执行方式，避免前端依赖或浏览器环境成为验证前提。

备选方案：

- 仅保留 API 入口：不利于本地快速验收，也增加权限和网络路径依赖。
- 仅保留分散脚本：不利于统一日志和报告。

### 5. 报告同时输出 machine-readable 和 human-readable 两类产物

建议至少输出：

- JSON：供脚本、CI、自动归档和二次分析使用
- Markdown：供人工 review 和变更记录引用

报告内容包含：运行时间、环境标识、执行项列表、每项状态、耗时、关键响应摘要、失败原因和整体结论。

### 6. 第三方适配器保持可替换，验证层只依赖 provider contract

验证框架不应把实现锁死在某一个厂商 SDK 上，而应复用或补充现有 adapter contract。这样未来替换 Qwen 兼容网关、MinerU 部署方式或 OSS 提供商时，主要变化集中在 adapter 层和 verifier 配置，而不是整套测试框架。

## Risks / Trade-offs

- [真实 API 存在费用消耗] → 通过小输入、受控测试集、分项执行和环境开关限制成本。
- [第三方限流或瞬时故障会造成假阴性] → 记录 provider error、HTTP 状态、request id，并为幂等测试项提供有限重试。
- [日志可能误打敏感信息] → 统一对 prompt、文件内容、base64 图片和长期凭证做脱敏或摘要化。
- [环境差异导致“本地能过、线上不过”] → 报告中写入环境标签、关键配置摘要和版本信息。
- [实时 ASR / Vision 这类能力更难稳定复现] → 固定输入样本、固定 timeout、记录模型与参数，并区分连接失败、模型失败和输出校验失败。

## Migration Plan

1. 先定义 capability spec、报告契约和 verifier 边界。
2. 在后端新增 verification runner、provider-specific verifiers 和统一日志 / 报告模型。
3. 补充可复跑命令、合成测试样本、环境变量说明和执行文档。
4. 在 apply 阶段逐项接通 OSS、MinerU、Qwen、数据库和 pgvector 的真实验证。
5. 通过集成报告确认可用后，再把该流程纳入联调和上线前验收基线。

若回滚，只需停止使用 verification runner 或移除新增集成验证模块，不影响现有产品原型和业务服务主路径。

## Open Questions

- Realtime ASR 的真实验证采用官方实时 WebSocket 兼容网关，还是当前项目已有的 provider 抽象先做一层封装？
- MinerU 在目标环境中采用本地服务、自托管容器，还是远程解析服务？
- Integration Report 是否需要写入数据库留档，还是先以文件产物为主？
- Rerank 与 Embedding 是否由同一供应商提供，还是需要独立的 provider capability matrix？
